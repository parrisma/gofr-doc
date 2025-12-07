"""Session-related exceptions."""

from typing import Optional, Dict, Any
from gofr_common.exceptions import ValidationError, ResourceNotFoundError


class SessionError(ValidationError):
    """Base exception for session-related errors."""

    pass



class SessionNotFoundError(ResourceNotFoundError):
    """Raised when a session cannot be found."""

    def __init__(self, session_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="SESSION_NOT_FOUND",
            message=f"Session '{session_id}' not found",
            details=details or {},
        )
        self.session_id = session_id


class SessionValidationError(SessionError):
    """Raised when session operation validation fails."""

    pass


class InvalidSessionStateError(SessionError):
    """Raised when session is in an invalid state for the requested operation."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(code="INVALID_SESSION_STATE", message=message, details=details or {})
