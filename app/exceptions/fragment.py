"""Fragment not found exception."""
from typing import Optional, List
from gofr_common.exceptions import RegistryError


class FragmentNotFoundError(RegistryError):
    """Raised when a fragment referenced by a template cannot be found."""
    
    def __init__(self, fragment_id: str, template_id: str, group: str, available_fragments: Optional[List[str]] = None):
        """
        Args:
            fragment_id: ID of the fragment that was not found
            template_id: ID of the template that referenced it
            group: Group where the fragment should exist
            available_fragments: List of available fragments in the group
        """
        available_text = ""
        if available_fragments:
            fragment_list = ", ".join(available_fragments)
            available_text = f" Available fragments in group '{group}': {fragment_list}."
        
        message = (
            f"Fragment '{fragment_id}' referenced by template '{template_id}' "
            f"not found in group '{group}'.{available_text}"
        )
        super().__init__(message)
