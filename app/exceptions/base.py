"""Project-specific exception classes for GOFR_DOC application.

Base exceptions (GofrError, ValidationError, etc.) are provided by gofr_common.
This module re-exports them for backward compatibility and contains any
project-specific exceptions.
"""

# Re-export from gofr_common for backward compatibility
from gofr_common.exceptions import (
    GofrError,
    ValidationError,
    ResourceNotFoundError,
    SecurityError,
    ConfigurationError,
    RegistryError,
)

# Project-specific alias for backward compatibility
GofrDocError = GofrError

__all__ = [
    "GofrError",
    "GofrDocError",
    "ValidationError",
    "ResourceNotFoundError",
    "SecurityError",
    "ConfigurationError",
    "RegistryError",
]

