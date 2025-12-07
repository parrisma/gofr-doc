"""Custom exceptions for group-aware registries and rendering pipeline.

All exceptions include detailed error messages designed for LLM processing,
enabling intelligent error recovery and decision-making.

Base exceptions are re-exported from gofr_common.exceptions.
"""

# Re-export common exceptions from gofr_common
from gofr_common.exceptions import (
    GofrError,
    ValidationError,
    ResourceNotFoundError,
    SecurityError,
    ConfigurationError,
    RegistryError,
)

# Project-specific exceptions
from app.exceptions.template import TemplateNotFoundError
from app.exceptions.fragment import FragmentNotFoundError
from app.exceptions.group import GroupMismatchError
from app.exceptions.style import StyleNotFoundError
from app.exceptions.invalid_group import InvalidGroupError
from app.exceptions.session import (
    SessionError,
    SessionNotFoundError,
    SessionValidationError,
    InvalidSessionStateError,
)

# Project-specific alias for backward compatibility
GofrDocError = GofrError

__all__ = [
    # Base exceptions (from gofr_common)
    "GofrError",
    "GofrDocError",  # Alias for backward compatibility
    "ValidationError",
    "ResourceNotFoundError",
    "SecurityError",
    "ConfigurationError",
    "RegistryError",
    # Specific exceptions
    "TemplateNotFoundError",
    "FragmentNotFoundError",
    "GroupMismatchError",
    "StyleNotFoundError",
    "InvalidGroupError",
    "SessionError",
    "SessionNotFoundError",
    "SessionValidationError",
    "InvalidSessionStateError",
]

