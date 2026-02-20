"""Authentication helpers for MCP server.

Behavior must remain identical to the legacy helpers previously defined in
app/mcp_server/mcp_server.py.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from gofr_common.web import get_auth_header_from_context

from app.mcp_server.responses import ToolResponse, _error


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


def verify_auth(
    arguments: Dict[str, Any],
    require_token: bool,
    auth_service: Optional[Any],
    logger: Any,
) -> tuple[Optional[str], Optional[ToolResponse]]:
    """Verify authentication and extract group from JWT token.

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
