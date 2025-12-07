"""Template not found exception."""
from typing import Optional, List
from gofr_common.exceptions import RegistryError


class TemplateNotFoundError(RegistryError):
    """Raised when a template cannot be found."""
    
    def __init__(self, template_id: str, groups: Optional[List[str]] = None, searched_groups: Optional[List[str]] = None):
        """
        Args:
            template_id: ID of the template that was not found
            groups: List of groups that were searched
            searched_groups: Specific groups that were searched
        """
        if searched_groups:
            groups_text = ", ".join(searched_groups)
            message = (
                f"Template '{template_id}' not found in groups: {groups_text}. "
                f"Available templates must be in one of these groups."
            )
        else:
            message = f"Template '{template_id}' not found in any loaded group"
        
        super().__init__(message)
