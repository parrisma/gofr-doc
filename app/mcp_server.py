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


def _json_text(payload: Dict[str, Any]) -> TextContent:
    return TextContent(type="text", text=json.dumps(payload, indent=2, ensure_ascii=True))


def _success(data: Any, message: Optional[str] = None) -> ToolResponse:
    payload: Dict[str, Any] = {"status": "success", "data": data}
    if message:
        payload["message"] = message
    return [_json_text(payload)]


def _error(code: str, message: str, recovery: str, details: Optional[Dict[str, Any]] = None) -> ToolResponse:
    error_model = ErrorResponse(
        error_code=code,
        message=message,
        recovery_strategy=recovery,
        details=details,
    )
    payload = {"status": "error", **error_model.model_dump(mode="json")}
    return [_json_text(payload)]


def _handle_validation_error(exc: PydanticValidationError) -> ToolResponse:
    details = {"validation_errors": exc.errors()}
    return _error(
        code="INVALID_ARGUMENTS",
        message="Input payload failed validation.",
        recovery="Review the validation errors, adjust the payload, and retry the call.",
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
                message="Authentication token is required for this operation.",
                recovery="Include a valid bearer token in the 'token' field and try again.",
            )
        return None

    try:
        auth_service.verify_token(token)
    except Exception as exc:  # pragma: no cover - depends on auth backend
        logger.warning("Token verification failed", error=str(exc))
        return _error(
            code="AUTH_FAILED",
            message=f"Token validation failed: {exc}",
            recovery="Obtain a valid token and retry the request.",
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
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    raise TypeError("Model does not support model_dump")


async def initialize_server() -> None:
    """Initialize server components."""
    logger.info("Initialising document MCP server")

    global template_registry, style_registry, session_store, session_manager, rendering_engine

    templates_dir = str(SysPath(__file__).parent.parent / "templates")
    styles_dir = str(SysPath(__file__).parent.parent / "styles")

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
            description="Simple health check returning server status and timestamp.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_templates",
            description="List all registered document templates.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_template_details",
            description="Fetch metadata and global parameter schema for a template.",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {"type": "string", "description": "Template identifier."},
                    "token": {"type": "string", "description": "Optional bearer token."},
                },
                "required": ["template_id"],
            },
        ),
        Tool(
            name="list_template_fragments",
            description="List fragment definitions available within a template.",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {"type": "string", "description": "Template identifier."},
                    "token": {"type": "string", "description": "Optional bearer token."},
                },
                "required": ["template_id"],
            },
        ),
        Tool(
            name="get_fragment_details",
            description="Retrieve parameter schema for a specific fragment.",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {"type": "string"},
                    "fragment_id": {"type": "string"},
                    "token": {"type": "string", "description": "Optional bearer token."},
                },
                "required": ["template_id", "fragment_id"],
            },
        ),
        Tool(
            name="list_styles",
            description="List all available rendering styles.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="create_document_session",
            description="Create a new document session for the specified template.",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {"type": "string"},
                    "token": {"type": "string", "description": "Optional bearer token."},
                },
                "required": ["template_id"],
            },
        ),
        Tool(
            name="set_global_parameters",
            description="Set or update global parameters for a document session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "parameters": {
                        "type": "object",
                        "description": "Dictionary of global parameters.",
                        "additionalProperties": True,
                    },
                    "token": {"type": "string", "description": "Bearer token when required."},
                },
                "required": ["session_id", "parameters"],
            },
        ),
        Tool(
            name="add_fragment",
            description="Add a fragment instance to the document body.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "fragment_id": {"type": "string"},
                    "parameters": {
                        "type": "object",
                        "description": "Fragment parameter values.",
                        "additionalProperties": True,
                    },
                    "position": {
                        "type": "string",
                        "description": "Insertion point: start, end, before:<guid>, or after:<guid>.",
                    },
                    "token": {"type": "string", "description": "Bearer token when required."},
                },
                "required": ["session_id", "fragment_id", "parameters"],
            },
        ),
        Tool(
            name="remove_fragment",
            description="Remove a fragment instance from a session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "fragment_instance_guid": {"type": "string"},
                    "token": {"type": "string", "description": "Bearer token when required."},
                },
                "required": ["session_id", "fragment_instance_guid"],
            },
        ),
        Tool(
            name="list_session_fragments",
            description="List the ordered fragments currently in a session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "token": {"type": "string", "description": "Bearer token when required."},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="abort_document_session",
            description="Abort a session and delete its persisted data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "token": {"type": "string", "description": "Bearer token when required."},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="get_document",
            description="Render the document for a session in the requested format (html, pdf, md).",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "format": {"type": "string", "enum": ["html", "pdf", "md"]},
                    "style_id": {
                        "type": "string",
                        "description": "Optional style identifier (defaults to registry default).",
                    },
                    "token": {"type": "string", "description": "Bearer token when required."},
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
        return _error(
            code="TEMPLATE_NOT_FOUND",
            message=f"Template '{payload.template_id}' is not registered.",
            recovery="Call list_templates to retrieve valid template identifiers before retrying.",
        )
    return _success(_model_dump(details))


async def _tool_list_template_fragments(arguments: Dict[str, Any]) -> ToolResponse:
    payload = ListTemplateFragmentsInput.model_validate(arguments)
    registry = _ensure_template_registry()
    schema = registry.get_template_schema(payload.template_id)
    if schema is None:
        return _error(
            code="TEMPLATE_NOT_FOUND",
            message=f"Template '{payload.template_id}' is not registered.",
            recovery="Call list_templates to retrieve valid template identifiers before retrying.",
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
        return _error(
            code="FRAGMENT_NOT_FOUND",
            message=(
                f"Fragment '{payload.fragment_id}' does not exist in template '{payload.template_id}'."
            ),
            recovery="Call list_template_fragments to inspect available fragment identifiers.",
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
            message=message or "Session is not ready for rendering.",
            recovery="Ensure global parameters are set and the session exists before rendering.",
        )

    session = await manager.get_session(payload.session_id)
    if session is None:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' could not be retrieved.",
            recovery="Create a new session or verify the session identifier before retrying.",
        )

    try:
        output = await renderer.render_document(
            session=session,
            output_format=OutputFormat(payload.format),
            style_id=payload.style_id,
        )
    except ValueError as exc:
        logger.warning("Rendering failed", error=str(exc))
        return _error(
            code="RENDER_FAILED",
            message=str(exc),
            recovery="Correct the session data or choose a different style/format, then retry.",
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
        return _error(
            code="UNKNOWN_TOOL",
            message=f"The tool '{name}' is not recognised.",
            recovery="Call list_tools to inspect supported tool names.",
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
