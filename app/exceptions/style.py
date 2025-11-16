"""Style not found exception."""
from typing import Optional, List
from app.exceptions.base import RegistryError


class StyleNotFoundError(RegistryError):
    """Raised when a style cannot be found."""
    
    def __init__(self, style_id: str, group: Optional[str] = None, available_styles: Optional[List[str]] = None):
        """
        Args:
            style_id: ID of the style that was not found
            group: Group where the style was expected
            available_styles: List of available styles
        """
        if group:
            group_text = f" in group '{group}'"
        else:
            group_text = ""
        
        available_text = ""
        if available_styles:
            style_list = ", ".join(available_styles)
            available_text = f" Available styles{group_text}: {style_list}."
        
        message = f"Style '{style_id}' not found{group_text}.{available_text}"
        super().__init__(message)
