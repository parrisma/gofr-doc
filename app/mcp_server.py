#!/usr/bin/env python3
"""Document generation MCP server."""

from __future__ import annotations

import asyncio
import contextlib
import json
import sys
from datetime import datetime
from pathlib import Path as SysPath
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Union

from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from pydantic import ValidationError as PydanticValidationError

# Ensure project root is on the import path when running directly
sys.path.insert(0, str(SysPath(__file__).parent.parent))

from app.auth import AuthService  # noqa: E402
from app.config import get_default_sessions_dir  # noqa: E402
from app.logger import Logger, session_logger  # noqa: E402
from app.rendering import RenderingEngine  # noqa: E402
from app.sessions import SessionManager, SessionStore  # noqa: E402
from app.styles import StyleRegistry  # noqa: E402
from app.templates import TemplateRegistry  # noqa: E402
from app.validation.document_models import (  # noqa: E402
    AbortDocumentSessionInput,
    AddFragmentInput,
    CreateDocumentSessionInput,
    ErrorResponse,
    FragmentDetailsOutput,
    FragmentListItem,
    GetDocumentInput,
    GetFragmentDetailsInput,
    GetTemplateDetailsInput,
    ListSessionFragmentsInput,
    ListTemplateFragmentsInput,
    OutputFormat,
    PingOutput,
    RemoveFragmentInput,
    SetGlobalParametersInput,
)

ToolResponse = List[Union[TextContent, ImageContent, EmbeddedResource]]
ToolHandler = Callable[[Dict[str, Any]], Awaitable[ToolResponse]]

app = Server("doco-document-service")
logger: Logger = session_logger

# Optional directory overrides (set by main_mcp.py for testing)
templates_dir_override: Optional[str] = None
styles_dir_override: Optional[str] = None

auth_service: Optional[AuthService] = None  # Injected by entrypoint

template_registry: Optional[TemplateRegistry] = None
style_registry: Optional[StyleRegistry] = None
session_store: Optional[SessionStore] = None
session_manager: Optional[SessionManager] = None
rendering_engine: Optional[RenderingEngine] = None

TOKEN_OPTIONAL_TOOLS = {
    "ping",
    "list_templates",
    "get_template_details",
    "list_template_fragments",
    "get_fragment_details",
    "list_styles",
}


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for non-standard types."""
    # Handle Pydantic models
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    # Handle dataclasses and regular objects
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    # Fallback
    return str(obj)


def _json_text(payload: Dict[str, Any]) -> TextContent:
    return TextContent(
        type="text",
        text=json.dumps(payload, indent=2, ensure_ascii=True, default=_json_serializer),
    )


def _success(data: Any, message: Optional[str] = None) -> ToolResponse:
    payload: Dict[str, Any] = {"status": "success", "data": data}
    if message:
        payload["message"] = message
    return [_json_text(payload)]


def _error(
    code: str, message: str, recovery: str, details: Optional[Dict[str, Any]] = None
) -> ToolResponse:
    error_model = ErrorResponse(
        error_code=code,
        message=message,
        recovery_strategy=recovery,
        details=details,
    )
    payload = {"status": "error", **error_model.model_dump(mode="json")}
    return [_json_text(payload)]


def _handle_validation_error(exc: PydanticValidationError) -> ToolResponse:
    errors = exc.errors()
    details = {"validation_errors": errors}

    # Build helpful recovery message based on error types
    missing_fields = [e["loc"][0] for e in errors if e["type"] == "missing"]
    invalid_types = [e["loc"][0] for e in errors if "type" in e["type"]]

    recovery_msg = "Input validation failed. "
    if missing_fields:
        recovery_msg += f"MISSING REQUIRED FIELDS: {', '.join(str(f) for f in missing_fields)}. "
    if invalid_types:
        recovery_msg += f"INCORRECT TYPES: {', '.join(str(f) for f in invalid_types)}. "
    recovery_msg += "Check the tool's inputSchema for required parameters and their types. Review the 'details' field below for specific errors, correct your input, and retry."

    return _error(
        code="INVALID_ARGUMENTS",
        message=f"Input payload failed validation. {len(errors)} error(s) found.",
        recovery=recovery_msg,
        details=details,
    )


def _verify_auth(arguments: Dict[str, Any], require_token: bool) -> Optional[ToolResponse]:
    if auth_service is None:
        return None

    token = arguments.get("token")
    if not token:
        if require_token:
            return _error(
                code="AUTH_REQUIRED",
                message="This operation requires authentication but no token was provided.",
                recovery=(
                    "AUTHENTICATION REQUIRED: Add a valid bearer token to your request. "
                    "Include: {'token': 'your_bearer_token_here'} in your tool arguments. "
                    "If you don't have a token, contact your administrator or check authentication documentation. "
                    "NOTE: Discovery tools (list_templates, get_template_details, list_styles) do NOT require authentication."
                ),
            )
        return None

    try:
        auth_service.verify_token(token)
    except Exception as exc:  # pragma: no cover - depends on auth backend
        logger.warning("Token verification failed", error=str(exc))
        error_str = str(exc).lower()

        recovery_msg = "Token validation failed. "
        if "expired" in error_str:
            recovery_msg += "TOKEN EXPIRED: Your authentication token has expired. Obtain a new token and retry the request."
        elif "invalid" in error_str or "malformed" in error_str:
            recovery_msg += "INVALID TOKEN FORMAT: The token format is incorrect. Verify you're using a valid JWT bearer token."
        else:
            recovery_msg += "The provided token could not be validated. Obtain a fresh authentication token and retry."

        return _error(
            code="AUTH_FAILED",
            message=f"Authentication failed: {exc}",
            recovery=recovery_msg,
        )
    return None


def _require_components() -> None:
    if not all([template_registry, style_registry, session_manager, rendering_engine]):
        raise RuntimeError("Server components have not been initialised")


def _ensure_template_registry() -> TemplateRegistry:
    _require_components()
    assert template_registry is not None
    return template_registry


def _ensure_style_registry() -> StyleRegistry:
    _require_components()
    assert style_registry is not None
    return style_registry


def _ensure_manager() -> SessionManager:
    _require_components()
    assert session_manager is not None
    return session_manager


def _ensure_renderer() -> RenderingEngine:
    _require_components()
    assert rendering_engine is not None
    return rendering_engine


def _model_dump(model: Any) -> Dict[str, Any]:
    """Convert model to dictionary, supporting Pydantic models and dataclasses."""
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    # Handle regular dataclasses and objects with __dict__
    if hasattr(model, "__dict__"):
        result = {}
        for key, value in model.__dict__.items():
            if hasattr(value, "model_dump"):
                # Nested Pydantic model
                result[key] = value.model_dump(mode="json")
            elif isinstance(value, list):
                # List might contain Pydantic models or regular objects
                converted_list = []
                for item in value:
                    if hasattr(item, "model_dump"):
                        converted_list.append(item.model_dump(mode="json"))
                    elif hasattr(item, "__dict__") and not isinstance(
                        item, (str, int, float, bool, type(None))
                    ):
                        converted_list.append(_model_dump(item))
                    else:
                        converted_list.append(item)
                result[key] = converted_list
            elif hasattr(value, "__dict__") and not isinstance(
                value, (str, int, float, bool, type(None))
            ):
                # Nested regular object - recursively convert it
                result[key] = _model_dump(value)
            else:
                result[key] = value
        return result
    raise TypeError(f"Cannot convert {type(model).__name__} to dictionary")


async def initialize_server() -> None:
    """Initialize server components."""
    logger.info("Initialising document MCP server")

    global template_registry, style_registry, session_store, session_manager, rendering_engine

    # Use overrides if provided (for testing), otherwise use defaults
    templates_dir = templates_dir_override or str(SysPath(__file__).parent.parent / "templates")
    styles_dir = styles_dir_override or str(SysPath(__file__).parent.parent / "styles")

    template_registry = TemplateRegistry(templates_dir=templates_dir, logger=logger)
    style_registry = StyleRegistry(styles_dir=styles_dir, logger=logger)
    session_store = SessionStore(base_dir=get_default_sessions_dir(), logger=logger)
    session_manager = SessionManager(
        session_store=session_store,
        template_registry=template_registry,
        logger=logger,
    )
    rendering_engine = RenderingEngine(
        template_registry=template_registry,
        style_registry=style_registry,
        logger=logger,
    )


@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    return [
        Tool(
            name="ping",
            description=(
                "Health check - Verify service availability. "
                "WORKFLOW: Use this first to confirm the service is responsive before making other requests. "
                "Returns server status and current timestamp."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_templates",
            description=(
                "Discovery - List all available document templates. "
                "WORKFLOW: Start here to discover which templates are available. Each template defines a document structure. "
                "Returns: Array of templates with template_id (use this in create_document_session), name, description, and group. "
                "NEXT STEPS: Use get_template_details to inspect a specific template's requirements."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_template_details",
            description=(
                "Discovery - Get detailed schema for a specific template including required global parameters. "
                "WORKFLOW: Call this after list_templates to understand what global parameters a template requires. "
                "Returns: Template metadata, list of global parameters with types and requirements, embedded fragment definitions. "
                "NEXT STEPS: Use create_document_session with the template_id, then set_global_parameters with the required params. "
                "ERROR HANDLING: If template_id not found, call list_templates to get valid identifiers."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "Template identifier from list_templates (e.g., 'basic_report', 'invoice').",
                    },
                    "token": {
                        "type": "string",
                        "description": "Optional bearer token for authenticated access.",
                    },
                },
                "required": ["template_id"],
            },
        ),
        Tool(
            name="list_template_fragments",
            description=(
                "Discovery - List all fragments available within a specific template. "
                "WORKFLOW: After selecting a template, call this to see what content fragments you can add to the document body. "
                "Returns: Array of fragments with fragment_id (use in add_fragment), name, description, and parameter_count. "
                "NEXT STEPS: Use get_fragment_details to see what parameters each fragment requires before calling add_fragment. "
                "ERROR HANDLING: If template_id not found, call list_templates first."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "Template identifier from list_templates.",
                    },
                    "token": {"type": "string", "description": "Optional bearer token."},
                },
                "required": ["template_id"],
            },
        ),
        Tool(
            name="get_fragment_details",
            description=(
                "Discovery - Get parameter schema for a specific fragment to understand what data it needs. "
                "WORKFLOW: Call this before add_fragment to discover required/optional parameters and their types. "
                "Returns: Fragment metadata, parameter definitions with types, defaults, examples, and validation rules. "
                "NEXT STEPS: Collect the required parameter values, then call add_fragment with the parameters object. "
                "ERROR HANDLING: If fragment_id not found, call list_template_fragments to see available fragments."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {"type": "string", "description": "Template identifier."},
                    "fragment_id": {
                        "type": "string",
                        "description": "Fragment identifier from list_template_fragments (e.g., 'heading', 'paragraph', 'table').",
                    },
                    "token": {"type": "string", "description": "Optional bearer token."},
                },
                "required": ["template_id", "fragment_id"],
            },
        ),
        Tool(
            name="list_styles",
            description=(
                "Discovery - List all available visual styles for document rendering. "
                "WORKFLOW: Optional - call this before get_document to see styling options. "
                "Returns: Array of styles with style_id (use in get_document), name, and description. "
                "NEXT STEPS: Use the style_id in get_document's style_id parameter to apply custom styling. "
                "DEFAULT: If not specified, the default style is automatically applied."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="create_document_session",
            description=(
                "Session Management - Create a new document session based on a template. This is REQUIRED before building content. "
                "WORKFLOW: After discovering templates with list_templates and understanding requirements with get_template_details, create a session. "
                "Returns: session_id (SAVE THIS - you'll need it for all subsequent operations), template_id, creation timestamps. "
                "NEXT STEPS: (1) Call set_global_parameters to set required template parameters, (2) Call add_fragment repeatedly to build document content, (3) Call get_document to render. "
                "ERROR HANDLING: If template_id not found, call list_templates to get valid identifiers. "
                "IMPORTANT: Sessions persist across API calls - the session_id is your handle to the document being built."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "Template identifier from list_templates. The template defines the document structure.",
                    },
                    "token": {
                        "type": "string",
                        "description": "Optional bearer token for authenticated sessions.",
                    },
                },
                "required": ["template_id"],
            },
        ),
        Tool(
            name="set_global_parameters",
            description=(
                "Session Configuration - Set or update global parameters that apply to the entire document (e.g., title, author, date). "
                "WORKFLOW: Call this after create_document_session to configure template-wide settings. Can be called multiple times to update parameters. "
                "Returns: Updated session state with current global_parameters. "
                "NEXT STEPS: After setting globals, use add_fragment to build the document body content. "
                "ERROR HANDLING: If session_id not found, create a new session with create_document_session. "
                "TIP: Use get_template_details to see what global parameters are required for your template before calling this."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier from create_document_session.",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Dictionary of global parameter values. Keys match parameter names from template schema. Example: {'title': 'Q4 Report', 'author': 'John Doe', 'date': '2025-11-16'}",
                        "additionalProperties": True,
                    },
                    "token": {
                        "type": "string",
                        "description": "Bearer token if session requires authentication.",
                    },
                },
                "required": ["session_id", "parameters"],
            },
        ),
        Tool(
            name="add_fragment",
            description=(
                "Content Building - Add a content fragment (e.g., heading, paragraph, table) to the document body. Call repeatedly to build up content. "
                "WORKFLOW: After create_document_session and set_global_parameters, call this to add each piece of content. Fragments are added in order. "
                "Returns: fragment_instance_guid (unique ID for this specific fragment instance - save it to remove or reorder later), position confirmation. "
                "NEXT STEPS: Continue calling add_fragment for additional content. When done, call get_document to render the final output. "
                "ERROR HANDLING: If fragment_id not found, call list_template_fragments. If parameters invalid, call get_fragment_details to see requirements. "
                "TIP: Use get_fragment_details first to understand what parameters each fragment type requires."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier from create_document_session.",
                    },
                    "fragment_id": {
                        "type": "string",
                        "description": "Fragment type from list_template_fragments (e.g., 'heading', 'paragraph', 'bullet_list', 'table').",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Fragment-specific parameters. Use get_fragment_details to see required fields. Example for 'heading': {'text': 'Chapter 1', 'level': 1}",
                        "additionalProperties": True,
                    },
                    "position": {
                        "type": "string",
                        "description": "Where to insert: 'end' (default, append to bottom), 'start' (prepend to top), 'before:<guid>' (insert before fragment with guid), 'after:<guid>' (insert after fragment with guid).",
                    },
                    "token": {"type": "string", "description": "Bearer token if required."},
                },
                "required": ["session_id", "fragment_id", "parameters"],
            },
        ),
        Tool(
            name="remove_fragment",
            description=(
                "Content Editing - Remove a specific fragment instance from the document. "
                "WORKFLOW: To remove content, use the fragment_instance_guid returned from add_fragment or found in list_session_fragments. "
                "Returns: Confirmation of removal with updated fragment count. "
                "NEXT STEPS: Continue editing with add_fragment or remove_fragment, then call get_document when ready. "
                "ERROR HANDLING: If guid not found, call list_session_fragments to see current fragments and their GUIDs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session identifier."},
                    "fragment_instance_guid": {
                        "type": "string",
                        "description": "Unique identifier for the specific fragment instance to remove (from add_fragment response or list_session_fragments).",
                    },
                    "token": {"type": "string", "description": "Bearer token if required."},
                },
                "required": ["session_id", "fragment_instance_guid"],
            },
        ),
        Tool(
            name="list_session_fragments",
            description=(
                "Session Inspection - List all fragments currently in the document in their display order. "
                "WORKFLOW: Call this to inspect the current document structure, get fragment GUIDs for removal, or verify your changes. "
                "Returns: Ordered array of fragments with guid (for remove_fragment), fragment_id, parameters, creation timestamp, and position. "
                "NEXT STEPS: Use the guid values with remove_fragment to delete content, or continue building with add_fragment. "
                "TIP: This shows the current state of your document before rendering."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session identifier."},
                    "token": {"type": "string", "description": "Bearer token if required."},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="abort_document_session",
            description=(
                "Session Cleanup - Permanently delete a session and all its data. Use this to clean up abandoned or test sessions. "
                "WORKFLOW: Call when you want to discard a document session and free up resources. "
                "Returns: Confirmation of deletion. "
                "WARNING: This is irreversible. All fragments and parameters in the session will be permanently deleted. "
                "ALTERNATIVE: If you just want to modify the document, use remove_fragment or set_global_parameters instead."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier to delete.",
                    },
                    "token": {"type": "string", "description": "Bearer token if required."},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="get_document",
            description=(
                "Final Rendering - Generate the finished document in your chosen format (HTML, PDF, or Markdown). "
                "WORKFLOW: After create_document_session, set_global_parameters, and adding fragments with add_fragment, call this to render. "
                "Returns: Rendered document content in requested format with metadata (format, session_id, render timestamp, success status). "
                "FORMATS: 'html' (web display), 'pdf' (printable, base64-encoded), 'md' or 'markdown' (plain text with markdown). "
                "STYLING: Optionally specify style_id from list_styles, or omit for default styling. "
                "PROXY MODE: Set proxy=true to store the rendered document on the server and receive a proxy_guid for later retrieval instead of the full content. "
                "ERROR HANDLING: If session not ready, verify global parameters are set and fragments added. If session_id not found, check the ID or create a new session. "
                "TIP: You can call this multiple times with different formats to get the same document in different outputs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier from create_document_session.",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["html", "pdf", "md"],
                        "description": "Output format: 'html' (web/display), 'pdf' (print-ready, base64), 'md' (markdown for text processing).",
                    },
                    "style_id": {
                        "type": "string",
                        "description": "Optional styling: style identifier from list_styles (e.g., 'light', 'dark', 'bizlight'). Omit for default styling.",
                    },
                    "proxy": {
                        "type": "boolean",
                        "description": "If true, store rendered document on server and return proxy_guid instead of content for later retrieval.",
                    },
                    "token": {"type": "string", "description": "Bearer token if required."},
                },
                "required": ["session_id", "format"],
            },
        ),
    ]


async def _tool_ping(arguments: Dict[str, Any]) -> ToolResponse:
    output = PingOutput(
        status="ok",
        timestamp=datetime.utcnow().isoformat(),
        message="Document generation service is online.",
    )
    return _success(_model_dump(output))


async def _tool_list_templates(arguments: Dict[str, Any]) -> ToolResponse:
    registry = _ensure_template_registry()
    templates = [
        {
            "template_id": item.template_id,
            "name": item.name,
            "description": item.description,
            "group": item.group,
        }
        for item in registry.list_templates()
    ]
    return _success({"templates": templates})


async def _tool_get_template_details(arguments: Dict[str, Any]) -> ToolResponse:
    payload = GetTemplateDetailsInput.model_validate(arguments)
    registry = _ensure_template_registry()
    details = registry.get_template_details(payload.template_id)
    if details is None:
        # Get available templates to help with recovery
        available = [t.template_id for t in registry.list_templates()]
        return _error(
            code="TEMPLATE_NOT_FOUND",
            message=f"Template '{payload.template_id}' does not exist in the registry.",
            recovery=f"Call list_templates to discover available templates. Available options: {', '.join(available) if available else 'none'}. Then retry with a valid template_id.",
        )
    return _success(_model_dump(details))


async def _tool_list_template_fragments(arguments: Dict[str, Any]) -> ToolResponse:
    payload = ListTemplateFragmentsInput.model_validate(arguments)
    registry = _ensure_template_registry()
    schema = registry.get_template_schema(payload.template_id)
    if schema is None:
        available = [t.template_id for t in registry.list_templates()]
        return _error(
            code="TEMPLATE_NOT_FOUND",
            message=f"Template '{payload.template_id}' does not exist. Cannot list fragments for non-existent template.",
            recovery=f"First call list_templates to discover available templates: {', '.join(available) if available else 'none available'}. Then retry with a valid template_id.",
        )

    fragments = [
        FragmentListItem(
            fragment_id=fragment.fragment_id,
            name=fragment.name,
            description=fragment.description,
            parameter_count=len(fragment.parameters),
        ).model_dump(mode="json")
        for fragment in schema.fragments
    ]
    return _success({"template_id": payload.template_id, "fragments": fragments})


async def _tool_get_fragment_details(arguments: Dict[str, Any]) -> ToolResponse:
    payload = GetFragmentDetailsInput.model_validate(arguments)
    registry = _ensure_template_registry()
    fragment_schema = registry.get_fragment_schema(payload.template_id, payload.fragment_id)
    if fragment_schema is None:
        # Get available fragments to help with recovery
        template_schema = registry.get_template_schema(payload.template_id)
        if template_schema:
            available_fragments = [f.fragment_id for f in template_schema.fragments]
            return _error(
                code="FRAGMENT_NOT_FOUND",
                message=f"Fragment '{payload.fragment_id}' does not exist in template '{payload.template_id}'.",
                recovery=f"Call list_template_fragments(template_id='{payload.template_id}') to see available fragments: {', '.join(available_fragments)}. Then retry with a valid fragment_id.",
            )
        else:
            return _error(
                code="FRAGMENT_NOT_FOUND",
                message=f"Fragment '{payload.fragment_id}' not found. Template '{payload.template_id}' may not exist.",
                recovery="First verify the template exists by calling list_templates, then call list_template_fragments to see available fragments.",
            )

    details = FragmentDetailsOutput(
        template_id=payload.template_id,
        fragment_id=fragment_schema.fragment_id,
        name=fragment_schema.name,
        description=fragment_schema.description,
        parameters=fragment_schema.parameters,
    )
    return _success(_model_dump(details))


async def _tool_list_styles(arguments: Dict[str, Any]) -> ToolResponse:
    registry = _ensure_style_registry()
    styles = [
        {
            "style_id": item.style_id,
            "name": item.name,
            "description": item.description,
        }
        for item in registry.list_styles()
    ]
    return _success({"styles": styles})


async def _tool_create_session(arguments: Dict[str, Any]) -> ToolResponse:
    payload = CreateDocumentSessionInput.model_validate(arguments)
    manager = _ensure_manager()
    output = await manager.create_session(template_id=payload.template_id, group=payload.group)
    return _success(_model_dump(output))


async def _tool_set_global_parameters(arguments: Dict[str, Any]) -> ToolResponse:
    payload = SetGlobalParametersInput.model_validate(arguments)
    manager = _ensure_manager()
    output = await manager.set_global_parameters(payload.session_id, payload.parameters)
    return _success(_model_dump(output))


async def _tool_add_fragment(arguments: Dict[str, Any]) -> ToolResponse:
    payload = AddFragmentInput.model_validate(arguments)
    manager = _ensure_manager()
    output = await manager.add_fragment(
        session_id=payload.session_id,
        fragment_id=payload.fragment_id,
        parameters=payload.parameters,
        position=payload.position or "end",
    )
    return _success(_model_dump(output))


async def _tool_remove_fragment(arguments: Dict[str, Any]) -> ToolResponse:
    payload = RemoveFragmentInput.model_validate(arguments)
    manager = _ensure_manager()
    output = await manager.remove_fragment(
        session_id=payload.session_id,
        fragment_instance_guid=payload.fragment_instance_guid,
    )
    return _success(_model_dump(output))


async def _tool_list_session_fragments(arguments: Dict[str, Any]) -> ToolResponse:
    payload = ListSessionFragmentsInput.model_validate(arguments)
    manager = _ensure_manager()
    output = await manager.list_session_fragments(session_id=payload.session_id)
    return _success(_model_dump(output))


async def _tool_abort_session(arguments: Dict[str, Any]) -> ToolResponse:
    payload = AbortDocumentSessionInput.model_validate(arguments)
    manager = _ensure_manager()
    output = await manager.abort_session(session_id=payload.session_id)
    return _success(_model_dump(output))


async def _tool_get_document(arguments: Dict[str, Any]) -> ToolResponse:
    payload = GetDocumentInput.model_validate(arguments)
    manager = _ensure_manager()
    renderer = _ensure_renderer()

    valid, message = await manager.validate_session_for_render(payload.session_id)
    if not valid:
        return _error(
            code="SESSION_NOT_READY",
            message=message
            or "Session is not ready for rendering. Required global parameters may be missing.",
            recovery=(
                "STEP 1: Call list_session_fragments to verify fragments are added. "
                "STEP 2: Call get_template_details to check required global parameters. "
                "STEP 3: Call set_global_parameters to provide missing values. "
                "STEP 4: Retry get_document."
            ),
        )

    session = await manager.get_session(payload.session_id)
    if session is None:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' does not exist or has been deleted.",
            recovery=(
                "The session may have been aborted or never created. "
                "STEP 1: Call create_document_session with a valid template_id to start a new session. "
                "STEP 2: Save the returned session_id. "
                "STEP 3: Build content with set_global_parameters and add_fragment. "
                "STEP 4: Retry get_document with the new session_id."
            ),
        )

    try:
        # Convert 'md' alias to 'markdown' for OutputFormat enum
        format_value = payload.format
        if format_value == "md":
            format_value = "markdown"

        output = await renderer.render_document(
            session=session,
            output_format=OutputFormat(format_value),
            style_id=payload.style_id,
            proxy=payload.proxy,
        )
    except ValueError as exc:
        logger.warning("Rendering failed", error=str(exc))
        error_msg = str(exc)
        recovery_steps = "Review the error details and adjust the session configuration. "

        if "style" in error_msg.lower():
            recovery_steps += "STYLE ERROR: Call list_styles to see available style_id values, then retry with a valid style_id or omit style_id to use the default."
        elif "format" in error_msg.lower():
            recovery_steps += "FORMAT ERROR: Use format='html', 'pdf', or 'md' only."
        else:
            recovery_steps += "Call list_session_fragments to verify content, and get_template_details to check requirements."

        return _error(
            code="RENDER_FAILED",
            message=f"Document rendering failed: {error_msg}",
            recovery=recovery_steps,
        )

    return _success(_model_dump(output))


HANDLERS: Dict[str, ToolHandler] = {
    "ping": _tool_ping,
    "list_templates": _tool_list_templates,
    "get_template_details": _tool_get_template_details,
    "list_template_fragments": _tool_list_template_fragments,
    "get_fragment_details": _tool_get_fragment_details,
    "list_styles": _tool_list_styles,
    "create_document_session": _tool_create_session,
    "set_global_parameters": _tool_set_global_parameters,
    "add_fragment": _tool_add_fragment,
    "remove_fragment": _tool_remove_fragment,
    "list_session_fragments": _tool_list_session_fragments,
    "abort_document_session": _tool_abort_session,
    "get_document": _tool_get_document,
}


@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> ToolResponse:
    logger.info("Tool invocation received", tool=name)

    handler = HANDLERS.get(name)
    if handler is None:
        logger.warning("Unknown tool requested", tool=name)
        available_tools = list(HANDLERS.keys())
        return _error(
            code="UNKNOWN_TOOL",
            message=f"Tool '{name}' does not exist in this service.",
            recovery=f"Available tools: {', '.join(available_tools)}. Call list_tools() to see detailed descriptions and schemas. Check for typos in the tool name.",
        )

    auth_error = _verify_auth(arguments, require_token=name not in TOKEN_OPTIONAL_TOOLS)
    if auth_error:
        return auth_error

    try:
        return await handler(arguments)
    except PydanticValidationError as exc:
        logger.warning("Payload validation error", tool=name, errors=len(exc.errors()))
        return _handle_validation_error(exc)
    except ValueError as exc:
        logger.warning("Business rule violation", tool=name, error=str(exc))
        return _error(
            code="INVALID_OPERATION",
            message=str(exc),
            recovery="Review the error message, adjust the request, and try again.",
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error("Unexpected tool failure", tool=name, error=str(exc))
        return _error(
            code="UNEXPECTED_ERROR",
            message=f"Unexpected error: {exc}",
            recovery="Check server logs for details and retry the request.",
        )


# ---------------------------------------------------------------------------
# Streamable HTTP integration
# ---------------------------------------------------------------------------


session_manager_http = StreamableHTTPSessionManager(
    app=app,
    event_store=None,
    json_response=False,
    stateless=False,
)


async def handle_streamable_http(scope, receive, send) -> None:
    await session_manager_http.handle_request(scope, receive, send)


@contextlib.asynccontextmanager
async def lifespan(starlette_app) -> AsyncIterator[None]:
    logger.info("Starting StreamableHTTP session manager")
    await initialize_server()
    async with session_manager_http.run():
        logger.info("StreamableHTTP session manager ready")
        yield


try:
    from starlette.applications import Starlette
    from starlette.middleware.cors import CORSMiddleware
    from starlette.routing import Mount
except ImportError as exc:  # pragma: no cover - import guard
    raise RuntimeError("Starlette is required for the MCP server") from exc


starlette_app = Starlette(
    debug=False,
    routes=[Mount("/mcp/", app=handle_streamable_http)],
    lifespan=lifespan,
)

starlette_app = CORSMiddleware(
    starlette_app,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE"],
    expose_headers=["Mcp-Session-Id"],
)


async def main(host: str = "0.0.0.0", port: int = 8011) -> None:
    import uvicorn

    logger.info("Starting document MCP server", host=host, port=port)
    config = uvicorn.Config(starlette_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":  # pragma: no cover - manual execution path
    asyncio.run(main())
