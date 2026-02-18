"""Session lifecycle tool handlers."""

from __future__ import annotations

from typing import Any, Dict

from app.mcp_server.responses import _error, _model_dump, _success
from app.mcp_server.state import ensure_manager
from app.mcp_server.tool_types import ToolResponse
from app.mcp_server.tools.common import resolve_session_identifier
from app.validation.document_models import AbortDocumentSessionInput, CreateDocumentSessionInput


async def _tool_create_session(arguments: Dict[str, Any]) -> ToolResponse:
    payload = CreateDocumentSessionInput.model_validate(arguments)
    manager = ensure_manager()
    output = await manager.create_session(
        template_id=payload.template_id, group=payload.group, alias=payload.alias
    )
    return _success(_model_dump(output))


async def _tool_get_session_status(arguments: Dict[str, Any]) -> ToolResponse:
    """Get current status of a document session."""
    from app.validation.document_models import GetSessionStatusInput

    payload = GetSessionStatusInput.model_validate(arguments)
    manager = ensure_manager()
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

    # Get session and verify group access
    session = await manager.get_session(session_id)
    if session is None:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery=(
                "Call list_active_sessions to see all available sessions in your group, "
                "or create_document_session to start a new session."
            ),
        )

    # SECURITY: Verify caller's group matches session's group
    if session.group != caller_group:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery=(
                "The session may not exist in your group. "
                "Call list_active_sessions to see sessions you have access to."
            ),
        )

    try:
        output = await manager.get_session_status(session_id)
        return _success(_model_dump(output))
    except ValueError as exc:
        return _error(
            code="SESSION_NOT_FOUND",
            message=str(exc),
            recovery=(
                "Call list_active_sessions to see all available sessions, "
                "or create_document_session to start a new session."
            ),
        )


async def _tool_list_active_sessions(arguments: Dict[str, Any]) -> ToolResponse:
    """List all active document sessions in caller's group."""
    from app.validation.document_models import ListActiveSessionsInput

    payload = ListActiveSessionsInput.model_validate(arguments)
    manager = ensure_manager()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # SECURITY: Only return sessions from caller's group
    all_sessions_output = await manager.list_active_sessions()
    filtered_sessions = [s for s in all_sessions_output.sessions if s.group == caller_group]

    all_sessions_output.sessions = filtered_sessions
    all_sessions_output.session_count = len(filtered_sessions)

    return _success(_model_dump(all_sessions_output))


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
    manager = ensure_manager()
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

    # SECURITY: Verify session belongs to caller's group
    session = await manager.get_session(session_id)
    if session is None or session.group != caller_group:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery=(
                "Verify the session_id or alias is correct and belongs to your group. "
                "Call list_active_sessions to see your sessions."
            ),
        )

    output = await manager.abort_session(session_id=session_id)
    return _success(_model_dump(output))
