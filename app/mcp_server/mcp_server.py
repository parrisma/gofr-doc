#!/usr/bin/env python3
"""Document generation MCP server with group-based security.

This server implements the Model Context Protocol (MCP) for document generation with
comprehensive group-based access control. All session operations verify that the caller's
JWT token group matches the session's group to prevent cross-group data access.

Security Model:
- JWT Authentication: Bearer tokens with {"group": "...", "exp": ..., "iat": ...}
- Group Isolation: Sessions, templates, styles, and fragments are isolated by group
- Directory Boundaries: data/docs/{templates,styles,sessions}/{group}/
- Session Verification: All operations verify session.group == caller_group
- Discovery Tools: list_templates, get_template_details, etc. do NOT require authentication

Authentication Flow:
1. Client sends JWT token in Authorization: Bearer header
2. _verify_auth() extracts and validates token -> returns (auth_group, error)
3. handle_call_tool() injects auth_group into tool arguments
4. Tool handlers verify session.group == auth_group before operations
5. Generic "SESSION_NOT_FOUND" errors prevent information leakage across groups
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path as SysPath
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Union

from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from pydantic import ValidationError as PydanticValidationError
from gofr_common.web import get_auth_header_from_context

# Ensure project root is on the import path when running directly
sys.path.insert(0, str(SysPath(__file__).parent.parent))

from app.auth import AuthService  # noqa: E402
from app.config import get_default_sessions_dir  # noqa: E402
from app.errors import map_error_for_mcp  # noqa: E402
from app.exceptions import GofrDocError  # noqa: E402
from app.logger import Logger, session_logger  # noqa: E402
from app.plot import GraphParams, GraphRenderer, GraphDataValidator  # noqa: E402
from app.plot.storage import PlotStorageWrapper  # noqa: E402
from app.storage.common_adapter import CommonStorageAdapter  # noqa: E402
from app.rendering import RenderingEngine  # noqa: E402
from app.sessions import SessionManager, SessionStore  # noqa: E402
from app.styles import StyleRegistry  # noqa: E402
from app.templates import TemplateRegistry  # noqa: E402
from app.validation.document_models import (  # noqa: E402
    AbortDocumentSessionInput,
    AddFragmentInput,
    AddImageFragmentInput,
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
from app.validation.plot_models import (  # noqa: E402
    AddPlotFragmentInput,
    GetImageInput,
    ListImagesInput,
    RenderGraphInput,
)

ToolResponse = List[Union[TextContent, ImageContent, EmbeddedResource]]
ToolHandler = Callable[[Dict[str, Any]], Awaitable[ToolResponse]]

app = Server("gofr-doc-document-service")
logger: Logger = session_logger

# Optional directory overrides (set by main_mcp.py for testing)
templates_dir_override: Optional[str] = None
styles_dir_override: Optional[str] = None

# Web server URL for proxy mode (set by main_mcp.py)
web_url_override: Optional[str] = None
proxy_url_mode: str = "url"  # "guid" or "url" - controls proxy response format

auth_service: Optional[AuthService] = None  # Injected by entrypoint

template_registry: Optional[TemplateRegistry] = None
style_registry: Optional[StyleRegistry] = None
session_store: Optional[SessionStore] = None
session_manager: Optional[SessionManager] = None
rendering_engine: Optional[RenderingEngine] = None

# Plot domain components (initialized in initialize_server)
plot_renderer: Optional[GraphRenderer] = None
plot_storage: Optional[PlotStorageWrapper] = None
plot_validator: Optional[GraphDataValidator] = None

TOKEN_OPTIONAL_TOOLS = {
    "ping",
    "help",
    "list_templates",
    "get_template_details",
    "list_template_fragments",
    "get_fragment_details",
    "list_styles",
    "list_themes",
    "list_handlers",
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


def _verify_auth(
    arguments: Dict[str, Any], require_token: bool
) -> tuple[Optional[str], Optional[ToolResponse]]:
    """
    Verify authentication and extract group from JWT token.

    Returns:
        Tuple of (group, error):
        - group: The authenticated group name if token is valid, None if no auth provided
        - error: ToolResponse error if auth failed, None if auth succeeded or not required
    """
    if auth_service is None:
        return None, None

    # Try auth_token first (gofr-dig convention), then legacy 'token' for backward compat
    token = arguments.get("auth_token") or arguments.get("token")

    # Strip "Bearer " prefix if present (gofr-dig tolerates both forms)
    if token and token.startswith("Bearer "):
        token = token[7:]

    # If not in arguments, try to extract from context (set by HTTP middleware)
    if not token:
        auth_header = get_auth_header_from_context()
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Strip "Bearer " prefix

    if not token:
        if require_token:
            return None, _error(
                code="AUTH_REQUIRED",
                message="This operation requires authentication but no token was provided.",
                recovery=(
                    "AUTHENTICATION REQUIRED: Add a valid bearer token to your request via HTTP Authorization header. "
                    "Use: Authorization: Bearer your_bearer_token_here. "
                    "Alternatively, include {'auth_token': 'your_bearer_token_here'} in tool arguments (preferred), "
                    "or {'token': 'your_bearer_token_here'} for backward compatibility. "
                    "If you don't have a token, contact your administrator or check authentication documentation. "
                    "NOTE: Discovery tools (list_templates, get_template_details, list_styles, list_themes, list_handlers) do NOT require authentication."
                ),
            )
        return None, None

    try:
        token_info = auth_service.verify_token(token)
        return token_info.groups[0] if token_info.groups else None, None
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

        return None, _error(
            code="AUTH_FAILED",
            message=f"Authentication failed: {exc}",
            recovery=recovery_msg,
        )


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
    global plot_renderer, plot_storage, plot_validator

    # Use overrides if provided (for testing), otherwise use defaults
    templates_dir = templates_dir_override or str(
        SysPath(__file__).parent.parent.parent / "data" / "templates"
    )
    styles_dir = styles_dir_override or str(
        SysPath(__file__).parent.parent.parent / "data" / "styles"
    )

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

    # Initialize plot domain components
    from app.storage import get_storage

    plot_renderer = GraphRenderer(logger=logger)
    plot_validator = GraphDataValidator()
    storage_adapter_raw = get_storage()
    if not isinstance(storage_adapter_raw, CommonStorageAdapter):
        logger.warning(
            "Plot storage requires CommonStorageAdapter but got legacy storage. "
            "Plot proxy mode will not work.",
        )
        plot_storage = None
    else:
        plot_storage = PlotStorageWrapper(storage=storage_adapter_raw, logger=logger)
    logger.info("Plot domain components initialized")


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
            name="help",
            description=(
                "Comprehensive Documentation - Get complete workflow guidance, GUID lifecycle rules, common pitfalls, "
                "and a step-by-step authoring guide for creating your own templates, fragments, and styles. "
                "WORKFLOW: Call this anytime you need help understanding the service workflow or troubleshooting issues. "
                "Returns: Service overview, GUID persistence rules (when session_ids and fragment_instance_guids are created/deleted), "
                "common mistakes to avoid, example workflows, tool sequencing guide, and content authoring reference. "
                "CRITICAL TOPICS COVERED: How long GUIDs persist, when to save them, workflow best practices, parameter requirements, "
                "how to create new templates/fragments/styles with correct YAML schemas and directory layout. "
                "USE THIS: When starting a new task, when confused about workflow, when encountering repeated errors, "
                "or when you need to create custom templates or fragments."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_session_status",
            description=(
                "Session Inspection - Get current state of a document session including readiness for rendering. "
                "WORKFLOW: Use this to verify a session exists and check its current state before performing operations. "
                "Returns: session_id, template_id, has_global_parameters (bool), fragment_count, is_ready_to_render (bool), timestamps. "
                "USEFUL FOR: Verifying old session_ids still exist, checking if globals are set, seeing fragment count before rendering. "
                "ERROR RECOVERY: If you get 'session not found' errors, call this first to verify the session_id is valid. "
                "GROUP SECURITY: Can only access sessions from your authenticated group. Returns 'SESSION_NOT_FOUND' for sessions in other groups. "
                "AUTHENTICATION: Requires JWT Bearer token. Generic errors prevent information leakage about sessions in other groups."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
                    },
                    "token": {"type": "string", "description": "Optional bearer token."},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="list_active_sessions",
            description=(
                "Session Discovery - List all available document sessions with summary information including their friendly aliases. "
                "WORKFLOW: Use this to see all existing sessions, discover session aliases, recover lost session identifiers, or check session states. "
                "Returns: Array of session summaries with session_id, alias (friendly name), template_id, fragment_count, has_global_parameters, timestamps. "
                "ALIASES: Each session has a friendly alias (e.g., 'invoice-march', 'weekly-report') that's easier to remember than UUIDs. "
                "Use the alias in other tools - they accept either session_id (UUID) or alias for identification. "
                "USEFUL FOR: Finding a session alias you forgot, discovering available sessions by name, seeing all in-progress documents, understanding session state. "
                "RECOVERY: If you lost a session identifier, call this to find both the UUID and friendly alias. "
                "GROUP ISOLATION: Only returns sessions from your authenticated group. You will NOT see sessions created by other groups. "
                "AUTHENTICATION: Requires JWT Bearer token to determine which group's sessions to return."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="validate_parameters",
            description=(
                "Parameter Validation - Check if parameters are valid BEFORE saving them to avoid errors. "
                "WORKFLOW: Call this before set_global_parameters or add_fragment to catch mistakes early. "
                "Returns: is_valid (bool), detailed errors array with parameter names, expected types, received types, examples. "
                "USEFUL FOR: Pre-flight validation, understanding parameter requirements, debugging validation errors. "
                "PARAMETERS: Set parameter_type='global' for template globals, 'fragment' for fragment parameters. "
                "ERROR DETAILS: Each error includes parameter name, expected type, what you provided, and example values. "
                "\n"
                "TABLE FRAGMENT VALIDATION: When validating table parameters, common errors to check:\n"
                "- rows must be non-empty array of arrays with consistent column counts\n"
                "- column_widths total must not exceed 100% (e.g., {0: '40%', 1: '60%'} is valid, {0: '60%', 1: '50%'} fails)\n"
                "- column indices in number_format, highlight_columns, column_widths must be valid (0-based, less than column count)\n"
                "- row indices in highlight_rows must be valid (0-based, less than row count)\n"
                "- colors must be theme names ('primary', 'success', etc.) or valid hex codes ('#4A90E2')\n"
                "- sort_by column references must exist (column name if has_header=true, or valid column index)\n"
                "Use this tool to catch these before calling add_fragment!\n"
                "\n"
                "GROUP SECURITY: Validates against templates in your authenticated group. Returns 'TEMPLATE_NOT_FOUND' for templates in other groups. "
                "AUTHENTICATION: Requires JWT Bearer token for group-based template access."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "Template identifier to validate against.",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Parameters to validate (the actual values you want to check).",
                    },
                    "parameter_type": {
                        "type": "string",
                        "enum": ["global", "fragment"],
                        "description": "Type of parameters: 'global' for template globals, 'fragment' for fragment parameters.",
                        "default": "global",
                    },
                    "fragment_id": {
                        "type": "string",
                        "description": "Required when parameter_type='fragment'. Fragment identifier from list_template_fragments.",
                    },
                    "token": {"type": "string", "description": "Optional bearer token."},
                },
                "required": ["template_id", "parameters", "parameter_type"],
            },
        ),
        Tool(
            name="list_templates",
            description=(
                "Discovery - List all available document templates. "
                "WORKFLOW: Start here to discover which templates are available. Each template defines a document structure. "
                "Returns: Array of templates with template_id (use this in create_document_session), name, description, and group. "
                "NEXT STEPS: Use get_template_details to inspect a specific template's requirements. "
                "AUTHENTICATION: No authentication required - this is a discovery tool available to all clients."
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
                "ERROR HANDLING: If template_id not found, call list_templates first. "
                "\n"
                "NOTE: The 'table' fragment (if available in the template) is highly capable with 14 parameters supporting:\n"
                "financial formatting (currency/percent/decimal), theme colors, row/column highlighting, sorting, and precise column width control. "
                "Always call get_fragment_details for 'table' to see its full capabilities before use."
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
                "ERROR HANDLING: If fragment_id not found, call list_template_fragments to see available fragments. "
                "\n"
                "IMPORTANT FOR TABLE FRAGMENTS: The 'table' fragment has 14 powerful parameters including:\n"
                "- Data structure (rows, has_header, title, width)\n"
                "- Layout control (column_alignments, column_widths with percentage-based sizing)\n"
                "- Visual styling (border_style, zebra_stripe, compact mode)\n"
                "- Number formatting (currency with any ISO code, percent, decimal precision, accounting notation)\n"
                "- Color theming (header_color, stripe_color, highlight_rows, highlight_columns - supports 8 theme colors + hex)\n"
                "- Data sorting (sort_by with single/multi-column support, numeric/string detection)\n"
                "Call this tool with fragment_id='table' to see detailed specifications for each parameter."
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
                "Returns: session_id (UUID), alias (friendly name), template_id, creation timestamps. "
                "NEXT STEPS: (1) Call set_global_parameters to set required template parameters, (2) Call add_fragment repeatedly to build document content, (3) Call get_document to render. "
                "ERROR HANDLING: If template_id not found, call list_templates to get valid identifiers. If alias already exists, choose a different name. "
                "IMPORTANT: Sessions persist across API calls - use either session_id (UUID) or alias in subsequent operations. Alias is easier for LLMs to remember. "
                "AUTHENTICATION: Requires JWT Bearer token. Session is bound to your group - you can only access sessions created by your group. "
                "GROUP ISOLATION: Sessions are isolated by group. Aliases are unique within a group but can be reused across groups."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "Template identifier from list_templates. The template defines the document structure.",
                    },
                    "alias": {
                        "type": "string",
                        "description": "Friendly name for this session (3-64 chars: letters, numbers, hyphens, underscores). Example: 'q4-report-2025', 'marketing-draft'. Use this instead of UUID in subsequent calls.",
                    },
                    "token": {
                        "type": "string",
                        "description": "Optional bearer token for authenticated sessions.",
                    },
                },
                "required": ["template_id", "alias"],
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
                "TIP: Use get_template_details to see what global parameters are required for your template before calling this. "
                "GROUP SECURITY: Can only modify sessions from your authenticated group. Returns 'SESSION_NOT_FOUND' for cross-group access attempts. "
                "AUTHENTICATION: Requires JWT Bearer token for session ownership verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
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
                "TIP: Use get_fragment_details first to understand what parameters each fragment type requires. "
                "\n\n"
                "TABLE FRAGMENT GUIDE: The 'table' fragment supports 14 parameters for rich tabular data:\n"
                "- REQUIRED: rows (array of arrays) - e.g., [['Name', 'Age'], ['Alice', '30']]\n"
                "- STRUCTURE: has_header (bool), title (string), width ('auto'|'full'|'80%')\n"
                "- LAYOUT: column_alignments (array: ['left', 'center', 'right']), column_widths (dict: {0: '40%', 1: '60%'} - must total <=100%)\n"
                "- STYLING: border_style ('full'|'horizontal'|'minimal'|'none'), zebra_stripe (bool), compact (bool)\n"
                "- FORMATTING: number_format (dict: {1: 'currency:USD', 2: 'percent'}) - supports currency:CODE, percent, decimal:N, integer, accounting\n"
                "- COLORS: header_color, stripe_color (theme: 'primary'|'success'|'warning'|'danger'|'info'|'light'|'dark'|'muted' OR hex: '#4A90E2')\n"
                "- HIGHLIGHTS: highlight_rows (dict: {0: 'success', 2: 'warning'}), highlight_columns (dict: {1: 'info'})\n"
                "- SORTING: sort_by (string column name | int column index | {column: 1, order: 'asc'|'desc'} | array for multi-column)\n"
                "\n"
                "EXAMPLE TABLE with all features:\n"
                "{'rows': [['Product','Q1','Q2','Q3'], ['Widget','1500','1800','2100'], ['Gadget','900','1200','1400']],\n"
                " 'has_header': True, 'title': 'Sales Report', 'width': 'full',\n"
                " 'column_alignments': ['left','right','right','right'], 'column_widths': {0: '40%', 1: '20%', 2: '20%', 3: '20%'},\n"
                " 'border_style': 'full', 'zebra_stripe': True, 'compact': False,\n"
                " 'number_format': {1: 'currency:USD', 2: 'currency:USD', 3: 'currency:USD'},\n"
                " 'header_color': 'primary', 'stripe_color': 'light', 'highlight_columns': {3: 'success'},\n"
                " 'sort_by': {'column': 3, 'order': 'desc'}}\n"
                "\n"
                "GROUP SECURITY: Can only add fragments to sessions from your authenticated group. Returns 'SESSION_NOT_FOUND' for cross-group access. "
                "AUTHENTICATION: Requires JWT Bearer token for session ownership verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
                    },
                    "fragment_id": {
                        "type": "string",
                        "description": "Fragment type from list_template_fragments (e.g., 'heading', 'paragraph', 'bullet_list', 'table').",
                    },
                    "parameters": {
                        "type": "object",
                        "description": (
                            "Fragment-specific parameters. Use get_fragment_details to see required fields. "
                            "Examples: "
                            "heading: {'text': 'Chapter 1', 'level': 1}, "
                            "paragraph: {'text': 'Content here', 'heading': 'Optional Section'}, "
                            "table: {'rows': [['A','B'],['1','2']], 'has_header': True, 'column_widths': {0: '60%', 1: '40%'}} - see tool description for full table capabilities. "
                            "NOTE: For images, use add_image_fragment tool instead of add_fragment - it provides immediate URL validation and format-specific rendering."
                        ),
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
            name="add_image_fragment",
            description=(
                "Content Building - Add an image from a URL to the document with immediate URL validation. "
                "\n\n"
                "NOTE: CRITICAL: URL VALIDATION HAPPENS IMMEDIATELY (not at render time)\n"
                "When you call this tool, the service immediately validates:\n"
                "1. URL format and accessibility (HTTP HEAD request)\n"
                "2. Content-Type header matches allowed image types\n"
                "3. Image size within limits (default 10MB max)\n"
                "4. HTTPS protocol (unless require_https=false)\n"
                "\n"
                "WORKFLOW: After create_document_session, call this to add images. URL must be publicly accessible.\n"
                "\n"
                "PARAMETERS:\n"
                "- REQUIRED: image_url (string) - Must be accessible URL returning valid image content-type\n"
                "- OPTIONAL: title (string) - Caption displayed above image\n"
                "- OPTIONAL: width (integer, pixels) - If only width set, height scales proportionally\n"
                "- OPTIONAL: height (integer, pixels) - If only height set, width scales proportionally\n"
                "- OPTIONAL: alt_text (string) - Accessibility text (defaults to title or 'Image')\n"
                "- OPTIONAL: alignment ('left'|'center'|'right') - Default: 'center'\n"
                "- OPTIONAL: require_https (bool) - Default: true (enforces HTTPS for security)\n"
                "- OPTIONAL: position (string) - Where to insert: 'end' (default), 'start', 'before:<guid>', 'after:<guid>'\n"
                "\n"
                "ALLOWED IMAGE TYPES:\n"
                "[Y] image/png, image/jpeg, image/jpg, image/gif, image/webp, image/svg+xml\n"
                "[N] PDFs, HTML, text files, etc. will be rejected\n"
                "\n"
                "RENDERING BEHAVIOR:\n"
                "- PDF/HTML: Image downloaded and embedded as base64 (no external dependencies)\n"
                "- Markdown: Image linked via URL (![alt](url) syntax)\n"
                "\n"
                "COMMON ERROR CODES & FIXES:\n"
                "- INVALID_IMAGE_URL: Non-HTTPS URL with require_https=true -> Use HTTPS or set require_https=false\n"
                "- IMAGE_URL_NOT_ACCESSIBLE: HTTP 404/403/500 -> Verify URL in browser, check if public\n"
                "- INVALID_IMAGE_CONTENT_TYPE: URL returns non-image type -> Ensure URL points to actual image file\n"
                "- IMAGE_TOO_LARGE: File > 10MB -> Compress image or use smaller version\n"
                "- IMAGE_URL_TIMEOUT: Slow/unreachable server -> Check network, try different CDN\n"
                "\n"
                "EXAMPLE - Basic image:\n"
                "{'image_url': 'https://example.com/logo.png', 'title': 'Company Logo', 'alignment': 'center'}\n"
                "\n"
                "EXAMPLE - Sized image with alt text:\n"
                "{'image_url': 'https://cdn.example.com/chart.png', 'width': 800, 'alt_text': 'Q4 Sales Chart', 'alignment': 'center'}\n"
                "\n"
                "EXAMPLE - Allow HTTP (dev/testing only):\n"
                "{'image_url': 'http://localhost:8000/test.jpg', 'require_https': False, 'title': 'Test Image'}\n"
                "\n"
                "TIP: Test URLs in browser first to verify accessibility and content-type!\n"
                "\n"
                "Returns: fragment_instance_guid if successful, or detailed error with recovery guidance.\n"
                "GROUP SECURITY: Can only add images to sessions from your authenticated group. "
                "AUTHENTICATION: Requires JWT Bearer token for session ownership verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
                    },
                    "image_url": {
                        "type": "string",
                        "description": (
                            "URL of the image to download and display. VALIDATED IMMEDIATELY via HTTP HEAD request. "
                            "Requirements: (1) Publicly accessible, (2) Returns 200 OK, (3) Content-Type is image/*, (4) Size <=10MB. "
                            "Allowed types: image/png, image/jpeg, image/jpg, image/gif, image/webp, image/svg+xml. "
                            "Example: 'https://cdn.example.com/images/logo.png'. "
                            "TIP: Test URL in browser first to verify it loads and shows image content-type."
                        ),
                    },
                    "title": {
                        "type": "string",
                        "description": (
                            "Optional title/caption displayed above the image. "
                            "Rendered as bold text or caption depending on output format. "
                            "Example: 'Figure 1: Sales Trends 2024'"
                        ),
                    },
                    "width": {
                        "type": "integer",
                        "description": (
                            "Target width in pixels (positive integer). "
                            "If only width specified, height scales proportionally to maintain aspect ratio. "
                            "If both width and height specified, image may be stretched/squashed. "
                            "Example: 800 for 800px wide. Leave unset to use original image size."
                        ),
                    },
                    "height": {
                        "type": "integer",
                        "description": (
                            "Target height in pixels (positive integer). "
                            "If only height specified, width scales proportionally to maintain aspect ratio. "
                            "If both width and height specified, image may be stretched/squashed. "
                            "Example: 600 for 600px tall. Leave unset to use original image size."
                        ),
                    },
                    "alt_text": {
                        "type": "string",
                        "description": (
                            "Alternative text for accessibility (screen readers, image load failures). "
                            "Should describe the image content for users who can't see it. "
                            "If not provided, defaults to title parameter or 'Image'. "
                            "Example: 'Bar chart showing quarterly revenue growth from Q1 to Q4 2024'"
                        ),
                    },
                    "alignment": {
                        "type": "string",
                        "enum": ["left", "center", "right"],
                        "description": (
                            "Image horizontal alignment within the document. "
                            "'left': Align to left margin, 'center': Center in page (default), 'right': Align to right margin. "
                            "Default: 'center' if not specified."
                        ),
                    },
                    "require_https": {
                        "type": "boolean",
                        "description": (
                            "Security setting for URL protocol validation. "
                            "If true (default): Only HTTPS URLs accepted - rejects http:// URLs. "
                            "If false: Allows both HTTPS and HTTP URLs (use for development/testing only). "
                            "Default: true. IMPORTANT: Set to false only for local testing (http://localhost)."
                        ),
                    },
                    "position": {
                        "type": "string",
                        "description": "Where to insert: 'end' (default), 'start', 'before:<guid>', 'after:<guid>'.",
                    },
                    "token": {"type": "string", "description": "Bearer token if required."},
                },
                "required": ["session_id", "image_url"],
            },
        ),
        Tool(
            name="remove_fragment",
            description=(
                "Content Editing - Remove a specific fragment instance from the document. "
                "WORKFLOW: To remove content, use the fragment_instance_guid returned from add_fragment or found in list_session_fragments. "
                "Returns: Confirmation of removal with updated fragment count. "
                "NEXT STEPS: Continue editing with add_fragment or remove_fragment, then call get_document when ready. "
                "ERROR HANDLING: If guid not found, call list_session_fragments to see current fragments and their GUIDs. "
                "GROUP SECURITY: Can only remove fragments from sessions in your authenticated group. Returns 'SESSION_NOT_FOUND' for cross-group access. "
                "AUTHENTICATION: Requires JWT Bearer token for session ownership verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
                    },
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
                "TIP: This shows the current state of your document before rendering. "
                "GROUP SECURITY: Can only list fragments from sessions in your authenticated group. Returns 'SESSION_NOT_FOUND' for cross-group access. "
                "AUTHENTICATION: Requires JWT Bearer token for session ownership verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
                    },
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
                "ALTERNATIVE: If you just want to modify the document, use remove_fragment or set_global_parameters instead. "
                "GROUP SECURITY: Can only delete sessions from your authenticated group. Returns 'SESSION_NOT_FOUND' for cross-group access. "
                "AUTHENTICATION: Requires JWT Bearer token for session ownership verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
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
                "PROXY MODE: Set proxy=true to store rendered document on server and receive proxy_guid + download_url instead of full content. "
                "  NOTE: IMPORTANT: proxy_guid is NOT the same as session_id! The proxy_guid is a unique identifier for the stored rendered document. "
                "  RESPONSE FIELDS: "
                "    - proxy_guid: Unique GUID for THIS rendered document (different from session_id) "
                "    - download_url: Complete HTTP URL to retrieve document: {web_server}/proxy/{proxy_guid} "
                "    - content: Will be null when proxy=true "
                "  RETRIEVAL: Use the download_url to GET the rendered document. The proxy_guid alone can also be used with /proxy/{proxy_guid} endpoint. "
                "  BENEFITS: Reduces network overhead for large documents (PDFs); persistent server-side storage for later retrieval. "
                "  EXAMPLE: get_document(session_id='abc-123', format='pdf', proxy=true) -> returns proxy_guid='xyz-789' and download_url='http://server:8012/proxy/xyz-789' "
                "ERROR HANDLING: If session not ready, verify global parameters are set and fragments added. If session_id not found, check the ID or create a new session. "
                "TIP: You can call this multiple times with different formats to get the same document in different outputs. "
                "GROUP SECURITY: Can only render documents from sessions in your authenticated group. Returns 'SESSION_NOT_FOUND' for cross-group access. "
                "AUTHENTICATION: Requires JWT Bearer token for session ownership verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
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
        # ====================================================================
        # Plot tools (migrated from gofr-plot)
        # ====================================================================
        Tool(
            name="render_graph",
            description=(
                "Render a graph visualization and return it as a base64-encoded image or storage GUID. "
                "\n\n**AUTHENTICATION**: Requires a valid JWT 'auth_token' parameter. "
                "\n\n**BASIC USAGE**: Provide 'title' (string) and at least one dataset (y1 array or legacy 'y' array). "
                "The 'x' parameter is optional - if omitted, indices [0, 1, 2, ...] are auto-generated. "
                "\n\n**MULTI-DATASET**: Supports up to 5 datasets (y1-y5) with optional labels (label1-label5) and colors (color1-color5). "
                "\n\n**CHART TYPES**: 'line' (default), 'scatter', or 'bar'. Use list_handlers tool to see descriptions. "
                "\n\n**THEMES**: 'light' (default), 'dark', 'bizlight', 'bizdark'. Use list_themes tool for details. "
                "\n\n**PROXY MODE**: Set proxy=true to save the image to persistent storage and receive a GUID instead of base64 data. "
                "Use get_image with the GUID to retrieve the image later. "
                "\n\n**OUTPUT FORMATS**: 'png' (default), 'jpg', 'svg', 'pdf'. "
                "\n\n**AXIS CONTROLS**: Optional parameters for axis limits (xmin/xmax/ymin/ymax) and custom tick positions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the graph"},
                    "x": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "X-axis data points (optional, defaults to indices)",
                    },
                    "y": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Y-axis data (backward compat - maps to y1)",
                    },
                    "y1": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "First dataset Y-axis data (required unless 'y' provided)",
                    },
                    "y2": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Second dataset (optional)",
                    },
                    "y3": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Third dataset (optional)",
                    },
                    "y4": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Fourth dataset (optional)",
                    },
                    "y5": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Fifth dataset (optional)",
                    },
                    "label1": {"type": "string", "description": "Label for first dataset (legend)"},
                    "label2": {"type": "string", "description": "Label for second dataset"},
                    "label3": {"type": "string", "description": "Label for third dataset"},
                    "label4": {"type": "string", "description": "Label for fourth dataset"},
                    "label5": {"type": "string", "description": "Label for fifth dataset"},
                    "color1": {
                        "type": "string",
                        "description": "Color for first dataset (e.g., 'red', '#FF5733')",
                    },
                    "color2": {"type": "string", "description": "Color for second dataset"},
                    "color3": {"type": "string", "description": "Color for third dataset"},
                    "color4": {"type": "string", "description": "Color for fourth dataset"},
                    "color5": {"type": "string", "description": "Color for fifth dataset"},
                    "xlabel": {
                        "type": "string",
                        "description": "X-axis label (default: 'X-axis')",
                        "default": "X-axis",
                    },
                    "ylabel": {
                        "type": "string",
                        "description": "Y-axis label (default: 'Y-axis')",
                        "default": "Y-axis",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["line", "scatter", "bar"],
                        "description": "Chart type (default: 'line')",
                        "default": "line",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["png", "jpg", "svg", "pdf"],
                        "description": "Image format (default: 'png')",
                        "default": "png",
                    },
                    "proxy": {
                        "type": "boolean",
                        "description": "If true, save to storage and return GUID (default: false)",
                        "default": False,
                    },
                    "alias": {
                        "type": "string",
                        "description": "Friendly name for proxy mode (3-64 chars, alphanumeric with hyphens/underscores)",
                    },
                    "color": {
                        "type": "string",
                        "description": "Line/marker color (backward compat, maps to color1)",
                    },
                    "line_width": {
                        "type": "number",
                        "description": "Line width (default: 2.0)",
                        "default": 2.0,
                    },
                    "marker_size": {
                        "type": "number",
                        "description": "Marker size for scatter (default: 36.0)",
                        "default": 36.0,
                    },
                    "alpha": {
                        "type": "number",
                        "description": "Transparency 0.0-1.0 (default: 1.0)",
                        "default": 1.0,
                    },
                    "theme": {
                        "type": "string",
                        "enum": ["light", "dark", "bizlight", "bizdark"],
                        "description": "Visual theme (default: 'light')",
                        "default": "light",
                    },
                    "xmin": {"type": "number", "description": "Minimum x-axis value"},
                    "xmax": {"type": "number", "description": "Maximum x-axis value"},
                    "ymin": {"type": "number", "description": "Minimum y-axis value"},
                    "ymax": {"type": "number", "description": "Maximum y-axis value"},
                    "x_major_ticks": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Custom x-axis major tick positions",
                    },
                    "y_major_ticks": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Custom y-axis major tick positions",
                    },
                    "x_minor_ticks": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Custom x-axis minor tick positions",
                    },
                    "y_minor_ticks": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Custom y-axis minor tick positions",
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (preferred). Include your JWT token here.",
                    },
                    "token": {
                        "type": "string",
                        "description": "JWT authentication token (legacy backward compatibility).",
                    },
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="get_image",
            description=(
                "Retrieve a previously stored graph image using its GUID or alias. "
                "\n\n**AUTHENTICATION**: Requires a valid JWT 'auth_token' parameter. "
                "The token's group must match the group that created the image. "
                "\n\n**IDENTIFIERS**: Use either a GUID or alias set during render_graph. "
                "\n\n**OUTPUT**: Returns the image as base64-encoded data with metadata."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "Image GUID or alias"},
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (preferred).",
                    },
                    "token": {
                        "type": "string",
                        "description": "JWT authentication token (legacy backward compatibility).",
                    },
                },
                "required": ["identifier"],
            },
        ),
        Tool(
            name="list_images",
            description=(
                "List all stored plot images accessible to your token's group. "
                "\n\n**AUTHENTICATION**: Requires a valid JWT 'auth_token' parameter. "
                "Only images belonging to your token's group will be listed. "
                "\n\n**OUTPUT**: Returns GUIDs, aliases, and metadata for stored plot images."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (preferred).",
                    },
                    "token": {
                        "type": "string",
                        "description": "JWT authentication token (legacy backward compatibility).",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="list_themes",
            description=(
                "Discover all available visual themes with descriptions. "
                "\n\n**AUTHENTICATION**: NOT required. "
                "\n\n**PURPOSE**: Use before calling render_graph to choose a theme. "
                "Available themes: 'light', 'dark', 'bizlight', 'bizdark'."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="list_handlers",
            description=(
                "Discover all available chart types with capability descriptions. "
                "\n\n**AUTHENTICATION**: NOT required. "
                "\n\n**PURPOSE**: Use before calling render_graph to choose the right chart type. "
                "Available types: 'line', 'scatter', 'bar'."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="add_plot_fragment",
            description=(
                "Render a graph and embed it as a fragment in a document session. "
                "\n\n**AUTHENTICATION**: Requires a valid JWT 'auth_token' parameter. "
                "\n\n**TWO MODES**: "
                "1. GUID path: Provide 'plot_guid' to embed a previously rendered plot. "
                "2. Inline path: Provide render params (title, y1, etc.) to render and embed in one call. "
                "\n\n**WORKFLOW**: "
                "- GUID: render_graph(proxy=true) -> get plot_guid -> add_plot_fragment(session_id, plot_guid=<guid>) "
                "- Inline: add_plot_fragment(session_id, title='My Chart', y1=[1,2,3]) "
                "\n\n**IMAGE EMBEDDING**: The plot is embedded as a base64 data URI in the document. "
                "Rendered HTML/PDF documents are self-contained - no external server needed to view plots."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Document session GUID or alias",
                    },
                    "plot_guid": {
                        "type": "string",
                        "description": "GUID of previously rendered plot (from render_graph with proxy=true)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Graph title (required for inline render, optional caption for GUID path)",
                    },
                    "x": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "X-axis data (optional)",
                    },
                    "y1": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "First dataset (required for inline render)",
                    },
                    "y2": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Second dataset (optional)",
                    },
                    "y3": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Third dataset (optional)",
                    },
                    "y4": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Fourth dataset (optional)",
                    },
                    "y5": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Fifth dataset (optional)",
                    },
                    "label1": {"type": "string", "description": "Label for first dataset"},
                    "label2": {"type": "string", "description": "Label for second dataset"},
                    "label3": {"type": "string", "description": "Label for third dataset"},
                    "label4": {"type": "string", "description": "Label for fourth dataset"},
                    "label5": {"type": "string", "description": "Label for fifth dataset"},
                    "color1": {"type": "string", "description": "Color for first dataset"},
                    "color2": {"type": "string", "description": "Color for second dataset"},
                    "color3": {"type": "string", "description": "Color for third dataset"},
                    "color4": {"type": "string", "description": "Color for fourth dataset"},
                    "color5": {"type": "string", "description": "Color for fifth dataset"},
                    "xlabel": {"type": "string", "description": "X-axis label"},
                    "ylabel": {"type": "string", "description": "Y-axis label"},
                    "type": {
                        "type": "string",
                        "enum": ["line", "scatter", "bar"],
                        "description": "Chart type",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["png", "jpg", "svg", "pdf"],
                        "description": "Image format",
                    },
                    "theme": {
                        "type": "string",
                        "enum": ["light", "dark", "bizlight", "bizdark"],
                        "description": "Visual theme",
                    },
                    "width": {"type": "integer", "description": "Image width in pixels"},
                    "height": {"type": "integer", "description": "Image height in pixels"},
                    "alt_text": {"type": "string", "description": "Accessibility text"},
                    "alignment": {
                        "type": "string",
                        "enum": ["left", "center", "right"],
                        "description": "Image alignment (default: center)",
                    },
                    "position": {
                        "type": "string",
                        "description": "Fragment position: 'end', 'start', 'before:<guid>', 'after:<guid>'",
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (preferred).",
                    },
                    "token": {
                        "type": "string",
                        "description": "JWT authentication token (legacy backward compatibility).",
                    },
                },
                "required": ["session_id"],
            },
        ),
    ]


def _resolve_session_identifier(identifier: str, group: str, manager) -> Optional[str]:
    """Resolve session identifier (alias or GUID) to session GUID.

    Args:
        identifier: Either a session alias or GUID
        group: Group context for alias resolution
        manager: SessionManager instance

    Returns:
        Session GUID if found, None otherwise
    """
    # Try to resolve as alias first, falls back to treating as GUID
    session_id = manager.resolve_session(group, identifier)
    if session_id:
        return session_id
    # If resolve_session returns None, check if it's a valid GUID that exists
    if manager._is_valid_uuid(identifier):
        return identifier
    return None


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
    output = await manager.create_session(
        template_id=payload.template_id, group=payload.group, alias=payload.alias
    )
    return _success(_model_dump(output))


async def _tool_set_global_parameters(arguments: Dict[str, Any]) -> ToolResponse:
    """Set global parameters for a document session.

    SECURITY: This operation verifies that the session belongs to the caller's group
    before allowing parameter updates. Returns generic SESSION_NOT_FOUND error for
    non-existent or cross-group sessions to prevent information leakage.

    Args:
        arguments: Dict containing session_id (or alias), parameters, and group (injected from JWT)

    Returns:
        ToolResponse with success or SESSION_NOT_FOUND error
    """
    payload = SetGlobalParametersInput.model_validate(arguments)
    manager = _ensure_manager()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # Resolve alias to GUID if needed
    session_id = _resolve_session_identifier(payload.session_id, caller_group, manager)
    if not session_id:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct. Call list_active_sessions to see your sessions.",
        )

    # SECURITY: Verify session belongs to caller's group
    session = await manager.get_session(session_id)
    if session is None or session.group != caller_group:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct and belongs to your group. Call list_active_sessions to see your sessions.",
        )

    output = await manager.set_global_parameters(session_id, payload.parameters)
    return _success(_model_dump(output))


async def _tool_add_fragment(arguments: Dict[str, Any]) -> ToolResponse:
    """Add a content fragment to a document session.

    SECURITY: This operation verifies that the session belongs to the caller's group
    before allowing fragment additions. Returns generic SESSION_NOT_FOUND error for
    non-existent or cross-group sessions to prevent information leakage.

    Args:
        arguments: Dict containing session_id (or alias), fragment_id, parameters, position, and group (injected from JWT)

    Returns:
        ToolResponse with success or SESSION_NOT_FOUND error
    """
    payload = AddFragmentInput.model_validate(arguments)
    manager = _ensure_manager()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # Resolve alias to GUID if needed
    session_id = _resolve_session_identifier(payload.session_id, caller_group, manager)
    if not session_id:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct. Call list_active_sessions to see your sessions.",
        )

    # SECURITY: Verify session belongs to caller's group
    session = await manager.get_session(session_id)
    if session is None or session.group != caller_group:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct and belongs to your group. Call list_active_sessions to see your sessions.",
        )

    output = await manager.add_fragment(
        session_id=session_id,
        fragment_id=payload.fragment_id,
        parameters=payload.parameters,
        position=payload.position or "end",
    )
    return _success(_model_dump(output))


async def _tool_add_image_fragment(arguments: Dict[str, Any]) -> ToolResponse:
    """Add a validated image fragment from URL to document session.

    SECURITY: Validates session belongs to caller's group.
    VALIDATION: Validates URL is accessible and returns valid image content-type
                at add time (not render time).

    Args:
        arguments: Dict containing session_id, image_url, optional parameters

    Returns:
        ToolResponse with success (including fragment_instance_guid) or detailed error
    """
    from datetime import datetime

    from app.validation.image_validator import ImageURLValidator

    # Parse and validate input
    payload = AddImageFragmentInput.model_validate(arguments)
    manager = _ensure_manager()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # Resolve alias to GUID if needed
    session_id = _resolve_session_identifier(payload.session_id, caller_group, manager)
    if not session_id:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct. Call list_active_sessions to see your sessions.",
        )

    # SECURITY: Verify session belongs to caller's group
    session = await manager.get_session(session_id)
    if session is None or session.group != caller_group:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct. Call list_active_sessions to see your sessions.",
        )

    # VALIDATION: Validate image URL
    validator = ImageURLValidator(logger=logger)
    validation_result = await validator.validate_image_url(
        url=payload.image_url, require_https=payload.require_https
    )

    if not validation_result.valid:
        error_details = validation_result.details or {}
        return _error(
            code=validation_result.error_code or "IMAGE_VALIDATION_ERROR",
            message=validation_result.error_message or "Image URL validation failed",
            recovery=error_details.get("recovery", "Check the URL and try again"),
            details=error_details,
        )

    # DOWNLOAD IMAGE: For HTML/PDF embedding, download and create data URI
    # For Markdown, we keep the original URL
    embedded_data_uri = None
    try:
        import httpx
        import base64

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(payload.image_url)
            response.raise_for_status()

            # Create data URI for embedding in HTML/PDF
            image_bytes = response.content
            content_type = validation_result.content_type or "image/png"
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            embedded_data_uri = f"data:{content_type};base64,{image_base64}"

            logger.info(f"Downloaded and embedded image: {len(image_bytes)} bytes")
    except Exception as e:
        logger.warning(f"Failed to download image for embedding: {e}. Will use URL fallback.")
        # If download fails, we'll still proceed with URL-only mode

    # Build fragment parameters with validation metadata
    fragment_parameters = {
        "image_url": payload.image_url,
        "validated_at": datetime.utcnow().isoformat() + "Z",
        "content_type": validation_result.content_type,
        "content_length": validation_result.content_length,
    }

    # Add embedded data URI if successfully downloaded
    if embedded_data_uri:
        fragment_parameters["embedded_data_uri"] = embedded_data_uri

    if payload.title:
        fragment_parameters["title"] = payload.title
    if payload.width:
        fragment_parameters["width"] = payload.width
    if payload.height:
        fragment_parameters["height"] = payload.height

    fragment_parameters["alt_text"] = payload.alt_text or payload.title or "Image"
    fragment_parameters["alignment"] = payload.alignment or "center"
    fragment_parameters["require_https"] = payload.require_https

    # Add fragment to session using standard fragment_id
    output = await manager.add_fragment(
        session_id=session_id,
        fragment_id="image_from_url",  # Standard fragment ID
        parameters=fragment_parameters,
        position=payload.position or "end",
    )
    return _success(_model_dump(output))


async def _tool_remove_fragment(arguments: Dict[str, Any]) -> ToolResponse:
    """Remove a content fragment from a document session.

    SECURITY: This operation verifies that the session belongs to the caller's group
    before allowing fragment removal. Returns generic SESSION_NOT_FOUND error for
    non-existent or cross-group sessions to prevent information leakage.

    Args:
        arguments: Dict containing session_id (or alias), fragment_instance_guid, and group (injected from JWT)

    Returns:
        ToolResponse with success or SESSION_NOT_FOUND error
    """
    payload = RemoveFragmentInput.model_validate(arguments)
    manager = _ensure_manager()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # Resolve alias to GUID if needed
    session_id = _resolve_session_identifier(payload.session_id, caller_group, manager)
    if not session_id:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct. Call list_active_sessions to see your sessions.",
        )

    # SECURITY: Verify session belongs to caller's group
    session = await manager.get_session(session_id)
    if session is None or session.group != caller_group:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct and belongs to your group. Call list_active_sessions to see your sessions.",
        )

    output = await manager.remove_fragment(
        session_id=session_id,
        fragment_instance_guid=payload.fragment_instance_guid,
    )
    return _success(_model_dump(output))


async def _tool_list_session_fragments(arguments: Dict[str, Any]) -> ToolResponse:
    """List all content fragments in a document session.

    SECURITY: This operation verifies that the session belongs to the caller's group
    before returning fragment information. Returns generic SESSION_NOT_FOUND error for
    non-existent or cross-group sessions to prevent information leakage.

    Args:
        arguments: Dict containing session_id (or alias) and group (injected from JWT)

    Returns:
        ToolResponse with fragment list or SESSION_NOT_FOUND error
    """
    payload = ListSessionFragmentsInput.model_validate(arguments)
    manager = _ensure_manager()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # Resolve alias to GUID if needed
    session_id = _resolve_session_identifier(payload.session_id, caller_group, manager)
    if not session_id:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct. Call list_active_sessions to see your sessions.",
        )

    # SECURITY: Verify session belongs to caller's group
    session = await manager.get_session(session_id)
    if session is None or session.group != caller_group:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct and belongs to your group. Call list_active_sessions to see your sessions.",
        )

    output = await manager.list_session_fragments(session_id=session_id)
    return _success(_model_dump(output))


async def _tool_abort_session(arguments: Dict[str, Any]) -> ToolResponse:
    """Abort and delete a document session.

    SECURITY: This operation verifies that the session belongs to the caller's group
    before allowing session deletion. Returns generic SESSION_NOT_FOUND error for
    non-existent or cross-group sessions to prevent information leakage.

    Args:
        arguments: Dict containing session_id (or alias) and group (injected from JWT)

    Returns:
        ToolResponse with success or SESSION_NOT_FOUND error
    """
    payload = AbortDocumentSessionInput.model_validate(arguments)
    manager = _ensure_manager()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # Resolve alias to GUID if needed
    session_id = _resolve_session_identifier(payload.session_id, caller_group, manager)
    if not session_id:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct. Call list_active_sessions to see your sessions.",
        )

    # SECURITY: Verify session belongs to caller's group
    session = await manager.get_session(session_id)
    if session is None or session.group != caller_group:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct and belongs to your group. Call list_active_sessions to see your sessions.",
        )

    output = await manager.abort_session(session_id=session_id)
    return _success(_model_dump(output))


async def _tool_get_document(arguments: Dict[str, Any]) -> ToolResponse:
    payload = GetDocumentInput.model_validate(arguments)
    manager = _ensure_manager()
    renderer = _ensure_renderer()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # Resolve alias to GUID if needed
    session_id = _resolve_session_identifier(payload.session_id, caller_group, manager)
    if not session_id:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct. Call list_active_sessions to see your sessions.",
        )

    # Get session first to verify it exists and check group
    session = await manager.get_session(session_id)
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

    # SECURITY: Verify session belongs to caller's group
    if session.group != caller_group:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="The session may not exist in your group. Call list_active_sessions to see sessions you have access to.",
        )

    valid, message = await manager.validate_session_for_render(session_id)
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

        # If proxy mode, conditionally add download URL based on proxy_url_mode
        if payload.proxy and output.proxy_guid:
            if proxy_url_mode == "url":
                # Construct the download URL for the web server
                # Priority: CLI flag > environment variable > default
                web_server_host = web_url_override or os.getenv(
                    "DOCO_WEB_URL", "http://localhost:8012"
                )
                output.download_url = f"{web_server_host}/proxy/{output.proxy_guid}"
            elif proxy_url_mode == "guid":
                # In guid-only mode, clear download_url to return just the GUID
                output.download_url = None

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


async def _tool_get_session_status(arguments: Dict[str, Any]) -> ToolResponse:
    """Get current status of a document session."""
    from app.validation.document_models import GetSessionStatusInput

    payload = GetSessionStatusInput.model_validate(arguments)
    manager = _ensure_manager()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # Resolve alias to GUID if needed
    session_id = _resolve_session_identifier(payload.session_id, caller_group, manager)
    if not session_id:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct. Call list_active_sessions to see your sessions.",
        )

    # Get session and verify group access
    session = await manager.get_session(session_id)
    if session is None:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Call list_active_sessions to see all available sessions in your group, or create_document_session to start a new session.",
        )

    # SECURITY: Verify caller's group matches session's group
    if session.group != caller_group:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="The session may not exist in your group. Call list_active_sessions to see sessions you have access to.",
        )

    try:
        output = await manager.get_session_status(session_id)
        return _success(_model_dump(output))
    except ValueError as exc:
        return _error(
            code="SESSION_NOT_FOUND",
            message=str(exc),
            recovery="Call list_active_sessions to see all available sessions, or create_document_session to start a new session.",
        )


async def _tool_list_active_sessions(arguments: Dict[str, Any]) -> ToolResponse:
    """List all active document sessions in caller's group."""
    from app.validation.document_models import ListActiveSessionsInput

    payload = ListActiveSessionsInput.model_validate(arguments)
    manager = _ensure_manager()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # SECURITY: Only return sessions from caller's group
    all_sessions_output = await manager.list_active_sessions()
    filtered_sessions = [s for s in all_sessions_output.sessions if s.group == caller_group]

    all_sessions_output.sessions = filtered_sessions
    all_sessions_output.session_count = len(filtered_sessions)

    return _success(_model_dump(all_sessions_output))


async def _tool_validate_parameters(arguments: Dict[str, Any]) -> ToolResponse:
    """Validate parameters without saving them."""
    from app.validation.document_models import ValidateParametersInput

    payload = ValidateParametersInput.model_validate(arguments)
    manager = _ensure_manager()
    registry = _ensure_template_registry()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # SECURITY: Verify template exists in caller's group
    template_schema = registry.get_template_schema(payload.template_id)
    if template_schema is None or template_schema.metadata.group != caller_group:
        return _error(
            code="TEMPLATE_NOT_FOUND",
            message=f"Template '{payload.template_id}' not found in your group",
            recovery="Call list_templates to see templates available in your group.",
        )

    try:
        output = await manager.validate_parameters(
            template_id=payload.template_id,
            parameters=payload.parameters,
            parameter_type=payload.parameter_type,
            fragment_id=payload.fragment_id,
        )
        return _success(_model_dump(output))
    except ValueError as exc:
        return _error(
            code="VALIDATION_ERROR",
            message=str(exc),
            recovery="Verify the template_id exists (call list_templates) and that fragment_id is valid (call list_template_fragments).",
        )


async def _tool_help(arguments: Dict[str, Any]) -> ToolResponse:
    """Provide comprehensive workflow documentation and guidance."""
    from app.validation.document_models import HelpOutput

    output = HelpOutput(
        service_name="gofr-doc-document-service",
        version="1.21.0",
        workflow_overview=(
            "WORKFLOW: DISCOVERY -> SESSION -> CONFIG -> BUILD -> RENDER\n"
            "1. DISCOVERY: list_templates, get_template_details, list_template_fragments\n"
            "2. SESSION: create_document_session\n"
            "3. CONFIG: set_global_parameters (title, author, etc.)\n"
            "4. BUILD: add_fragment repeatedly\n"
            "5. RENDER: get_document (HTML/PDF/Markdown)\n\n"
            "SECURITY: JWT Bearer token required for sessions. Group-isolated: you only see YOUR sessions.\n"
            "Discovery tools (list_templates, get_template_details, list_styles) do NOT need auth."
        ),
        guid_persistence=(
            "CRITICAL: UUID HANDLING (36-char format only)\n"
            "Format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx | Example: 61ea2281-c8df-4719-b71e-56a1305352cc\n"
            "[Y] Copy/paste EXACT | [N] Never retype (b71e != b77e) | [N] Never truncate | Case-sensitive\n\n"
            "THREE GUID TYPES:\n"
            "1. session_id: Document config (reusable, save immediately after create_document_session)\n"
            "2. fragment_instance_guid: Unique per add_fragment call (use to remove specific fragments)\n"
            "3. proxy_guid: One specific rendered output (DIFFERENT from session_id!)\n\n"
            "PROXY MODE (session_id != proxy_guid):\n"
            "session_id = recipe (reusable) | proxy_guid = baked cake (one specific render)\n"
            "One session -> many proxy_guids (different formats/styles)\n"
            "Download: GET /proxy/{proxy_guid} with Authorization header (NOT /proxy/{session_id}!)"
        ),
        common_pitfalls=[
            "Not saving session_id immediately after create_document_session",
            "Retyping/modifying UUIDs (b71e != b77e) or truncating them (61ea2281-... invalid)",
            "Global parameters AFTER fragments (must be BEFORE) | AVOID:  Wrong parameter names",
            "Confusing session_id (config/reusable) with proxy_guid (rendered/one-time)",
            "Downloading proxy via /proxy/{session_id} instead of /proxy/{proxy_guid}",
            "Missing Authorization header on proxy downloads",
            "TABLE: Widths total >100% | 1-based indices (use 0-based) | Capitalized colors",
            "TABLE: Missing # in hex | Wrong format ('USD' not 'currency:USD') | sort_by column name when no header",
            "IMAGE: Not testing URL in browser first | Behind login | Missing image/* Content-Type",
            "IMAGE: HTTP without require_https=false | Both width AND height (distorts) | >10MB",
        ],
        example_workflows=[
            {
                "name": "QUICK START: Create & Render Document",
                "steps": [
                    "1. list_templates() -> Pick a template_id",
                    "2. create_document_session(template_id='...') -> Save session_id",
                    "3. set_global_parameters(session_id='...', parameters={title: '...', author: '...'})",
                    "4. add_fragment(session_id='...', fragment_id='heading', parameters={text: '...'})",
                    "5. add_fragment(session_id='...', fragment_id='paragraph', parameters={text: '...'})",
                    "6. get_document(session_id='...', format='html') -> Get HTML directly",
                    "",
                    "ALTERNATIVE (for large docs):",
                    "6. get_document(session_id='...', format='pdf', proxy=true) -> Save proxy_guid",
                    "7. GET /proxy/{proxy_guid} with Authorization header -> Download PDF from web",
                ],
            },
            {
                "name": "Validate Before Adding",
                "steps": [
                    "validate_parameters(template_id='...', parameter_type='global', parameters={...})",
                    "validate_parameters(template_id='...', parameter_type='fragment', fragment_id='...', parameters={...})",
                    "Only call add_fragment/set_global_parameters if is_valid=true",
                ],
            },
            {
                "name": "Table with Formatting",
                "steps": [
                    "create_document_session -> set_global_parameters -> add_fragment with:",
                    "  rows: [[...]], has_header: true, column_widths: {0: '40%', 1: '30%', 2: '30%'},",
                    "  column_alignments: ['left','right','right'],",
                    "  number_format: {1: 'currency:USD', 2: 'decimal:2'},",
                    "  header_color: 'primary', zebra_stripe: true",
                ],
            },
            {
                "name": "Add Images",
                "steps": [
                    "1. Test image URL in browser first (must show Content-Type: image/*)",
                    "2. add_image_fragment(session_id='...', image_url='https://...', width=600, alignment='center')",
                    "3. If error, check error_code: INVALID_IMAGE_URL (use HTTPS), IMAGE_URL_NOT_ACCESSIBLE (check if public)",
                    "4. INVALID_IMAGE_CONTENT_TYPE (wrong format), IMAGE_TOO_LARGE (compress)",
                ],
            },
        ],
        tool_sequence=[
            {
                "category": "DISCOVERY",
                "tools": [
                    "ping",
                    "list_templates",
                    "get_template_details",
                    "list_template_fragments",
                    "get_fragment_details",
                    "list_styles",
                ],
            },
            {
                "category": "SESSION",
                "tools": [
                    "create_document_session",
                    "list_active_sessions",
                    "get_session_status",
                    "abort_document_session",
                ],
            },
            {"category": "VALIDATION", "tools": ["validate_parameters"]},
            {
                "category": "BUILD",
                "tools": [
                    "set_global_parameters",
                    "add_fragment",
                    "add_image_fragment",
                    "remove_fragment",
                    "list_session_fragments",
                ],
            },
            {"category": "RENDER", "tools": ["get_document"]},
        ],
        authoring_guide=[
            "All content lives under data/{templates,fragments,styles}/<group>/. The <group> directory name controls access isolation (e.g. public, team1).",
            "TEMPLATE: Directory is data/templates/<group>/<template_id>/. Required files: template.yaml (schema: metadata + global_parameters + fragments list), document.html.jinja2 (outer HTML wrapper receiving {{ title }}, {{ css }}, {{ fragments }}), and a fragments/ subdirectory with one .html.jinja2 per fragment declared in the YAML.",
            "template.yaml skeleton: metadata: {template_id: my_report, group: public, name: My Report, description: A custom report template}. global_parameters: [{name: title, type: string, required: true}, {name: author, type: string, required: false}]. fragments: [{fragment_id: paragraph, name: Paragraph, parameters: [{name: text, type: string, required: true}]}]",
            "document.html.jinja2 minimal example: <html><head><style>{{ css }}</style></head><body><h1>{{ title }}</h1>{% for f in fragments %}{{ f.html|safe }}{% endfor %}</body></html>",
            "Fragment Jinja2 example (fragments/paragraph.html.jinja2): <div class='fragment-paragraph'><p>{{ text }}</p></div>",
            "STANDALONE FRAGMENT: Directory is data/fragments/<group>/<fragment_id>/. Required files: fragment.yaml (schema: fragment_id, group, name, description, parameters) and fragment.html.jinja2 (Jinja2 template receiving declared parameters as variables).",
            "fragment.yaml skeleton: {fragment_id: callout, group: public, name: Callout Box, description: A highlighted callout, parameters: [{name: text, type: string, required: true}, {name: style, type: string, required: false, default: info}]}",
            "STYLE: Directory is data/styles/<group>/<style_id>/. Required files: style.yaml (metadata: style_id, group, name, description) and style.css (CSS injected into documents via {{ css }}).",
            "RULE: template_id / fragment_id / style_id MUST match their directory name.",
            "RULE: group field in YAML MUST match the parent group directory name.",
            "RULE: Parameter types are string, integer, number, boolean, array, object.",
            "RULE: Restart the service after adding new content (registries scan at startup).",
        ],
    )

    return _success(_model_dump(output))


# ========================================================================
# Plot tool handlers (migrated from gofr-plot)
# ========================================================================


async def _tool_render_graph(arguments: Dict[str, Any]) -> ToolResponse:
    """Render a graph visualization.

    Validates input, renders the graph, and returns either:
    - base64 image data (default mode)
    - storage GUID (proxy mode, for later retrieval via get_image)

    SECURITY: Requires valid JWT. Group isolation for proxy storage.
    """
    import base64 as b64_mod

    payload = RenderGraphInput.model_validate(arguments)
    caller_group = payload.group if hasattr(payload, "group") else "public"

    renderer = plot_renderer
    if renderer is None:
        return _error(
            code="PLOT_NOT_INITIALIZED",
            message="Plot subsystem is not initialized",
            recovery="The server may not have started correctly. Try restarting.",
        )

    storage = plot_storage
    validator = plot_validator

    # Build GraphParams from validated input (exclude auth/group fields)
    param_fields = {
        k: v
        for k, v in payload.model_dump().items()
        if k not in ("auth_token", "token", "group") and v is not None
    }

    try:
        graph_data = GraphParams(**param_fields)
    except (ValueError, Exception) as e:
        return _error(
            code="INVALID_GRAPH_PARAMS",
            message=f"Invalid graph parameters: {str(e)}",
            recovery="Check required fields: 'title' is required, at least y1 (or y) must be provided as a list of numbers.",
        )

    # Validate graph data
    if validator is not None:
        validation_result = validator.validate(graph_data)
        if not validation_result.is_valid:
            error_details = [err.to_dict() for err in validation_result.errors]
            return _error(
                code="GRAPH_VALIDATION_ERROR",
                message="Graph data validation failed",
                recovery="Review the validation errors and correct the input data.",
                details={"validation_errors": error_details},
            )

    # Proxy mode: render to bytes, save to storage, return GUID
    if graph_data.proxy:
        if storage is None:
            return _error(
                code="PLOT_STORAGE_NOT_INITIALIZED",
                message="Plot storage is not initialized",
                recovery="The server may not have started correctly. Try restarting.",
            )

        graph_data_bytes = graph_data.model_copy()
        object.__setattr__(graph_data_bytes, "return_base64", False)

        try:
            image_bytes = renderer.render(graph_data_bytes, group=caller_group)
            if isinstance(image_bytes, str):
                image_bytes = b64_mod.b64decode(image_bytes)
        except (ValueError, RuntimeError) as e:
            return _error(
                code="RENDER_ERROR",
                message=f"Graph rendering failed: {str(e)}",
                recovery="Check your data arrays and chart type. Ensure arrays are non-empty and of the same length.",
            )

        guid = storage.save_image(
            image_data=image_bytes,
            format=graph_data.format,
            group=caller_group,
            alias=graph_data.alias,
        )

        result = {
            "guid": guid,
            "format": graph_data.format,
            "theme": graph_data.theme,
            "type": graph_data.type,
            "title": graph_data.title,
            "size_bytes": len(image_bytes),
        }
        if graph_data.alias:
            result["alias"] = graph_data.alias

        logger.info(
            "Plot rendered in proxy mode",
            guid=guid,
            format=graph_data.format,
            group=caller_group,
        )
        return _success(result, message=f"Graph saved with GUID: {guid}")

    # Non-proxy: render to base64 and return as ImageContent
    try:
        graph_data_b64 = graph_data.model_copy()
        object.__setattr__(graph_data_b64, "return_base64", True)
        encoded = renderer.render(graph_data_b64, group=caller_group)
        if isinstance(encoded, bytes):
            encoded = b64_mod.b64encode(encoded).decode("utf-8")
    except (ValueError, RuntimeError) as e:
        return _error(
            code="RENDER_ERROR",
            message=f"Graph rendering failed: {str(e)}",
            recovery="Check your data arrays and chart type. Ensure arrays are non-empty and of the same length.",
        )

    mime_type = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "svg": "image/svg+xml",
        "pdf": "application/pdf",
    }.get(graph_data.format, "image/png")

    logger.info(
        "Plot rendered inline",
        format=graph_data.format,
        theme=graph_data.theme,
        chart_type=graph_data.type,
        group=caller_group,
    )

    return [
        ImageContent(type="image", data=encoded, mimeType=mime_type),
        _json_text(
            {
                "status": "success",
                "data": {
                    "format": graph_data.format,
                    "theme": graph_data.theme,
                    "type": graph_data.type,
                    "title": graph_data.title,
                },
            }
        ),
    ]


async def _tool_get_image(arguments: Dict[str, Any]) -> ToolResponse:
    """Retrieve a stored plot image by GUID or alias.

    SECURITY: Group isolation -- only images from the caller's group are accessible.
    """
    import base64 as b64_mod

    payload = GetImageInput.model_validate(arguments)
    caller_group = payload.group if hasattr(payload, "group") else "public"

    storage = plot_storage
    if storage is None:
        return _error(
            code="PLOT_STORAGE_NOT_INITIALIZED",
            message="Plot storage is not initialized",
            recovery="The server may not have started correctly. Try restarting.",
        )

    result = storage.get_image(payload.identifier, group=caller_group)
    if result is None:
        return _error(
            code="IMAGE_NOT_FOUND",
            message=f"Image '{payload.identifier}' not found",
            recovery="Check the GUID or alias is correct. Call list_images to see available images in your group.",
        )

    image_data, fmt = result
    encoded = b64_mod.b64encode(image_data).decode("utf-8")
    mime_type = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "svg": "image/svg+xml",
        "pdf": "application/pdf",
    }.get(fmt, "image/png")

    alias = storage.get_alias(
        storage.resolve_identifier(payload.identifier, caller_group) or payload.identifier
    )

    logger.info(
        "Plot image retrieved",
        identifier=payload.identifier,
        format=fmt,
        group=caller_group,
        size_bytes=len(image_data),
    )

    return [
        ImageContent(type="image", data=encoded, mimeType=mime_type),
        _json_text(
            {
                "status": "success",
                "data": {
                    "identifier": payload.identifier,
                    "format": fmt,
                    "size_bytes": len(image_data),
                    "alias": alias,
                },
            }
        ),
    ]


async def _tool_list_images(arguments: Dict[str, Any]) -> ToolResponse:
    """List all stored plot images accessible to the caller's group."""
    payload = ListImagesInput.model_validate(arguments)
    caller_group = payload.group if hasattr(payload, "group") else "public"

    storage = plot_storage
    if storage is None:
        return _error(
            code="PLOT_STORAGE_NOT_INITIALIZED",
            message="Plot storage is not initialized",
            recovery="The server may not have started correctly. Try restarting.",
        )

    images = storage.list_images(group=caller_group)

    logger.info(
        "Plot images listed",
        group=caller_group,
        count=len(images),
    )

    return _success(
        {"images": images, "count": len(images)},
        message=f"Found {len(images)} plot image(s) in group '{caller_group}'",
    )


async def _tool_list_themes(arguments: Dict[str, Any]) -> ToolResponse:
    """List all available plot themes with descriptions."""
    from app.plot.themes import list_themes_with_descriptions

    themes = list_themes_with_descriptions()
    return _success(
        {"themes": themes, "count": len(themes)},
        message=f"Found {len(themes)} available theme(s)",
    )


async def _tool_list_handlers(arguments: Dict[str, Any]) -> ToolResponse:
    """List all available chart types (handlers) with descriptions."""
    from app.plot.handlers import list_handlers_with_descriptions

    handlers = list_handlers_with_descriptions()
    return _success(
        {"handlers": handlers, "count": len(handlers)},
        message=f"Found {len(handlers)} available chart type(s)",
    )


async def _tool_add_plot_fragment(arguments: Dict[str, Any]) -> ToolResponse:
    """Render a graph and embed it as a fragment in a document session.

    Two modes:
    1. GUID path: Provide 'plot_guid' to embed a previously rendered plot.
    2. Inline path: Provide render params (title, y1, etc.) to render and embed.

    Both paths produce a base64 data URI embedded as an image_from_url fragment.

    SECURITY: Validates session belongs to caller's group.
    """
    import base64 as b64_mod
    from datetime import datetime

    payload = AddPlotFragmentInput.model_validate(arguments)
    manager = _ensure_manager()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # Resolve session alias to GUID if needed
    session_id = _resolve_session_identifier(payload.session_id, caller_group, manager)
    if not session_id:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct. Call list_active_sessions to see your sessions.",
        )

    # SECURITY: Verify session belongs to caller's group
    session = await manager.get_session(session_id)
    if session is None or session.group != caller_group:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id or alias is correct. Call list_active_sessions to see your sessions.",
        )

    # Determine mode: GUID path vs inline render path
    if payload.plot_guid:
        # GUID path: fetch previously rendered plot from storage
        storage = plot_storage
        if storage is None:
            return _error(
                code="PLOT_STORAGE_NOT_INITIALIZED",
                message="Plot storage is not initialized",
                recovery="The server may not have started correctly. Try restarting.",
            )

        data_uri = storage.get_image_as_data_uri(payload.plot_guid, group=caller_group)
        if data_uri is None:
            return _error(
                code="IMAGE_NOT_FOUND",
                message=f"Plot image '{payload.plot_guid}' not found",
                recovery="Check the GUID is correct and belongs to your group. Call list_images to see available images.",
            )

        # Use title from payload as caption, or derive from GUID
        image_title = payload.title or f"Plot {payload.plot_guid[:8]}"
        content_type = "image/png"  # Default for stored images

        logger.info(
            "Embedding plot from GUID",
            plot_guid=payload.plot_guid,
            session_id=session_id,
            group=caller_group,
        )

    else:
        # Inline render path: render the graph in-process
        if payload.title is None:
            return _error(
                code="MISSING_TITLE",
                message="'title' is required for inline render mode",
                recovery="Provide a 'title' parameter, or use 'plot_guid' to embed a previously rendered plot.",
            )

        renderer = plot_renderer
        if renderer is None:
            return _error(
                code="PLOT_NOT_INITIALIZED",
                message="Plot subsystem is not initialized",
                recovery="The server may not have started correctly. Try restarting.",
            )

        # Build GraphParams from inline render fields
        render_fields = {}
        for field_name in (
            "title",
            "x",
            "y",
            "y1",
            "y2",
            "y3",
            "y4",
            "y5",
            "label1",
            "label2",
            "label3",
            "label4",
            "label5",
            "color1",
            "color2",
            "color3",
            "color4",
            "color5",
            "color",
            "xlabel",
            "ylabel",
            "type",
            "format",
            "theme",
            "line_width",
            "marker_size",
            "alpha",
        ):
            val = getattr(payload, field_name, None)
            if val is not None:
                render_fields[field_name] = val

        try:
            graph_data = GraphParams(**render_fields)
        except (ValueError, Exception) as e:
            return _error(
                code="INVALID_GRAPH_PARAMS",
                message=f"Invalid graph parameters: {str(e)}",
                recovery="Check required fields: 'title' and at least y1 (or y) must be provided.",
            )

        # Validate
        validator = plot_validator
        if validator is not None:
            validation_result = validator.validate(graph_data)
            if not validation_result.is_valid:
                error_details = [err.to_dict() for err in validation_result.errors]
                return _error(
                    code="GRAPH_VALIDATION_ERROR",
                    message="Graph data validation failed",
                    recovery="Review the validation errors and correct the input data.",
                    details={"validation_errors": error_details},
                )

        # Render to bytes
        try:
            image_bytes = renderer.render_to_bytes(graph_data)
        except (ValueError, RuntimeError) as e:
            return _error(
                code="RENDER_ERROR",
                message=f"Graph rendering failed: {str(e)}",
                recovery="Check your data arrays and chart type.",
            )

        content_type = f"image/{graph_data.format}"
        if graph_data.format == "jpg":
            content_type = "image/jpeg"
        elif graph_data.format == "svg":
            content_type = "image/svg+xml"

        encoded = b64_mod.b64encode(image_bytes).decode("utf-8")
        data_uri = f"data:{content_type};base64,{encoded}"
        image_title = payload.title

        logger.info(
            "Embedding inline-rendered plot",
            chart_type=graph_data.type,
            session_id=session_id,
            group=caller_group,
        )

    # Build fragment parameters (same pattern as add_image_fragment)
    fragment_parameters: Dict[str, Any] = {
        "image_url": "inline:plot",  # Marker for inline content
        "embedded_data_uri": data_uri,
        "validated_at": datetime.utcnow().isoformat() + "Z",
        "content_type": content_type,
    }

    if image_title:
        fragment_parameters["title"] = image_title
    if payload.width:
        fragment_parameters["width"] = payload.width
    if payload.height:
        fragment_parameters["height"] = payload.height

    fragment_parameters["alt_text"] = payload.alt_text or image_title or "Plot"
    fragment_parameters["alignment"] = payload.alignment or "center"

    # Add fragment to session using standard image fragment
    output = await manager.add_fragment(
        session_id=session_id,
        fragment_id="image_from_url",
        parameters=fragment_parameters,
        position=payload.position or "end",
    )

    logger.info(
        "Plot fragment added to session",
        session_id=session_id,
        group=caller_group,
        mode="guid" if payload.plot_guid else "inline",
    )

    return _success(_model_dump(output))


HANDLERS: Dict[str, ToolHandler] = {
    "ping": _tool_ping,
    "help": _tool_help,
    "list_templates": _tool_list_templates,
    "get_template_details": _tool_get_template_details,
    "list_template_fragments": _tool_list_template_fragments,
    "get_fragment_details": _tool_get_fragment_details,
    "list_styles": _tool_list_styles,
    "get_session_status": _tool_get_session_status,
    "list_active_sessions": _tool_list_active_sessions,
    "validate_parameters": _tool_validate_parameters,
    "create_document_session": _tool_create_session,
    "set_global_parameters": _tool_set_global_parameters,
    "add_fragment": _tool_add_fragment,
    "add_image_fragment": _tool_add_image_fragment,
    "remove_fragment": _tool_remove_fragment,
    "list_session_fragments": _tool_list_session_fragments,
    "abort_document_session": _tool_abort_session,
    "get_document": _tool_get_document,
    # Plot tools
    "render_graph": _tool_render_graph,
    "get_image": _tool_get_image,
    "list_images": _tool_list_images,
    "list_themes": _tool_list_themes,
    "list_handlers": _tool_list_handlers,
    "add_plot_fragment": _tool_add_plot_fragment,
}


@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> ToolResponse:
    logger.info("Tool invocation started", tool=name, args_keys=list(arguments.keys()))

    handler = HANDLERS.get(name)
    if handler is None:
        logger.error("Unknown tool requested", tool=name, available_tools=list(HANDLERS.keys()))
        available_tools = list(HANDLERS.keys())
        return _error(
            code="UNKNOWN_TOOL",
            message=f"Tool '{name}' does not exist in this service.",
            recovery=f"Available tools: {', '.join(available_tools)}. Call list_tools() to see detailed descriptions and schemas. Check for typos in the tool name.",
        )

    auth_group, auth_error = _verify_auth(arguments, require_token=name not in TOKEN_OPTIONAL_TOOLS)
    if auth_error:
        return auth_error

    # SECURITY: Inject authenticated group from JWT token into arguments
    # This ensures all tools operate within the caller's group boundary.
    # The group from JWT token takes precedence over any 'group' field in arguments
    # to prevent clients from claiming access to other groups.
    if auth_group is not None:
        arguments["group"] = auth_group
        logger.debug("Authenticated group injected", tool=name, group=auth_group)
    # If no auth provided and no group in arguments, default to "public"
    elif "group" not in arguments:
        arguments["group"] = "public"
        logger.debug("No auth provided, defaulting to public group", tool=name)

    try:
        result = await handler(arguments)
        logger.info("Tool completed successfully", tool=name)
        return result
    except PydanticValidationError as exc:
        logger.error(
            "Validation error",
            tool=name,
            error_count=len(exc.errors()),
            errors=[{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()],
        )
        return _handle_validation_error(exc)
    except GofrDocError as exc:
        # Use the error mapper to convert structured domain exceptions
        logger.error(
            "Domain error",
            tool=name,
            error_code=exc.code,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        error_response = map_error_for_mcp(exc)
        return [_json_text({"status": "error", **error_response})]
    except ValueError as exc:
        # Legacy support for any remaining ValueError exceptions
        logger.error(
            "Business rule violation",
            tool=name,
            error_type="ValueError",
            error=str(exc),
        )
        return _error(
            code="INVALID_OPERATION",
            message=str(exc),
            recovery="Review the error message, adjust the request, and try again.",
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error(
            "Unexpected tool failure",
            tool=name,
            error_type=type(exc).__name__,
            error=str(exc),
        )
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


from gofr_common.web import (  # noqa: E402 - must import after MCP setup
    create_mcp_starlette_app,
    create_health_routes,
)

health_routes = create_health_routes(
    service="gofr-doc-mcp",
    auth_enabled=auth_service is not None,
)

starlette_app = create_mcp_starlette_app(
    mcp_handler=handle_streamable_http,
    lifespan=lifespan,
    env_prefix="GOFR_DOC",
    include_auth_middleware=True,
    additional_routes=health_routes,
)


async def main(host: str = "0.0.0.0", port: int = 8010) -> None:
    import uvicorn

    logger.info("Starting document MCP server", host=host, port=port)
    config = uvicorn.Config(starlette_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":  # pragma: no cover - manual execution path
    asyncio.run(main())
