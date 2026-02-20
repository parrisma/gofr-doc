"""Fragment tool handlers."""

from __future__ import annotations

from typing import Any, Dict

from app.logger import Logger, session_logger
from app.mcp_server.responses import _error, _model_dump, _success
from app.mcp_server.state import ensure_manager
from app.mcp_server.tool_types import ToolResponse
from app.mcp_server.tools.common import resolve_session_identifier
from app.validation.document_models import (
    AddFragmentInput,
    AddImageFragmentInput,
    ListSessionFragmentsInput,
    RemoveFragmentInput,
    SetGlobalParametersInput,
)

logger: Logger = session_logger


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
                "Verify the session_id or alias is correct. "
                "Call list_active_sessions to see your sessions."
            ),
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
        import base64

        import httpx

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

    output = await manager.list_session_fragments(session_id=session_id)
    return _success(_model_dump(output))
