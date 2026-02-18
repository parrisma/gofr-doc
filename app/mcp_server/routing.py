"""Tool routing and dispatch for MCP server."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import ValidationError as PydanticValidationError

from app.auth import AuthService
from app.errors import map_error_for_mcp
from app.exceptions import GofrDocError
from app.logger import Logger

from app.mcp_server.auth import TOKEN_OPTIONAL_TOOLS, verify_auth
from app.mcp_server.responses import _error, _handle_validation_error, _json_text
from app.mcp_server.tool_types import ToolHandler, ToolResponse

from app.mcp_server.tools.discovery import (
    _tool_get_fragment_details,
    _tool_get_template_details,
    _tool_help,
    _tool_list_styles,
    _tool_list_template_fragments,
    _tool_list_templates,
    _tool_ping,
)
from app.mcp_server.tools.fragments import (
    _tool_add_fragment,
    _tool_add_image_fragment,
    _tool_list_session_fragments,
    _tool_remove_fragment,
    _tool_set_global_parameters,
)
from app.mcp_server.tools.plot import (
    _tool_add_plot_fragment,
    _tool_get_image,
    _tool_list_handlers,
    _tool_list_images,
    _tool_list_themes,
    _tool_render_graph,
)
from app.mcp_server.tools.rendering import _tool_get_document
from app.mcp_server.tools.sessions import (
    _tool_abort_session,
    _tool_create_session,
    _tool_get_session_status,
    _tool_list_active_sessions,
)
from app.mcp_server.tools.validation import _tool_validate_parameters


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


async def dispatch_tool_call(
    *,
    name: str,
    arguments: Dict[str, Any],
    auth_service: Optional[AuthService],
    logger: Logger,
) -> ToolResponse:
    logger.info("Tool invocation started", tool=name, args_keys=list(arguments.keys()))

    handler = HANDLERS.get(name)
    if handler is None:
        logger.error("Unknown tool requested", tool=name, available_tools=list(HANDLERS.keys()))
        available_tools = list(HANDLERS.keys())
        return _error(
            code="UNKNOWN_TOOL",
            message=f"Tool '{name}' does not exist in this service.",
            recovery=(
                f"Available tools: {', '.join(available_tools)}. "
                "Call list_tools() to see detailed descriptions and schemas. "
                "Check for typos in the tool name."
            ),
        )

    auth_group, auth_error = verify_auth(
        arguments,
        require_token=name not in TOKEN_OPTIONAL_TOOLS,
        auth_service=auth_service,
        logger=logger,
    )
    if auth_error:
        return auth_error

    # SECURITY: Inject authenticated group from JWT token into arguments
    # The group from JWT token takes precedence over any 'group' field in arguments.
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
