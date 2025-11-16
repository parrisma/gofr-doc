"""Invalid group exception."""
from typing import Optional
from app.exceptions.base import RegistryError


class InvalidGroupError(RegistryError):
    """Raised when a group operation is invalid."""
    
    def __init__(self, group: str, reason: Optional[str] = None):
        """
        Args:
            group: Group name that caused the error
            reason: Explanation of why the group is invalid
        """
        if reason:
            message = f"Invalid group '{group}': {reason}"
        else:
            message = f"Invalid group '{group}'"
        super().__init__(message)
