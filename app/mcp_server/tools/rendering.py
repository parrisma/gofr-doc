"""Rendering tool handlers."""

from __future__ import annotations

import os
from typing import Any, Dict

from app.logger import Logger, session_logger
from app.mcp_server import runtime_settings
from app.mcp_server.responses import _error, _model_dump, _success
from app.mcp_server.state import ensure_manager, ensure_renderer
from app.mcp_server.tool_types import ToolResponse
from app.mcp_server.tools.common import resolve_session_identifier
from app.validation.document_models import GetDocumentInput, OutputFormat

logger: Logger = session_logger


async def _tool_get_document(arguments: Dict[str, Any]) -> ToolResponse:
    payload = GetDocumentInput.model_validate(arguments)
    manager = ensure_manager()
    renderer = ensure_renderer()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # Resolve alias to GUID if needed
    session_id = resolve_session_identifier(payload.session_id, caller_group, manager)
    if not session_id:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery=(
                "Verify the session_id or alias is correct. "
                "Call list_active_sessions to see your sessions."
            ),
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
            recovery=(
                "The session may not exist in your group. "
                "Call list_active_sessions to see sessions you have access to."
            ),
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
            if runtime_settings.proxy_url_mode == "url":
                # Construct the download URL for the web server
                # Priority: CLI flag > environment variable > default
                web_server_host = runtime_settings.web_url_override or os.getenv(
                    "DOCO_WEB_URL", "http://localhost:8012"
                )
                output.download_url = f"{web_server_host}/proxy/{output.proxy_guid}"
            elif runtime_settings.proxy_url_mode == "guid":
                # In guid-only mode, clear download_url to return just the GUID
                output.download_url = None

    except ValueError as exc:
        logger.warning("Rendering failed", error=str(exc))
        error_msg = str(exc)
        recovery_steps = "Review the error details and adjust the session configuration. "

        if "style" in error_msg.lower():
            recovery_steps += (
                "STYLE ERROR: Call list_styles to see available style_id values, "
                "then retry with a valid style_id or omit style_id to use the default."
            )
        elif "format" in error_msg.lower():
            recovery_steps += "FORMAT ERROR: Use format='html', 'pdf', or 'md' only."
        else:
            recovery_steps += (
                "Call list_session_fragments to verify content, "
                "and get_template_details to check requirements."
            )

        return _error(
            code="RENDER_FAILED",
            message=f"Document rendering failed: {error_msg}",
            recovery=recovery_steps,
        )

    return _success(_model_dump(output))
