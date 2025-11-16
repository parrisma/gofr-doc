"""Group mismatch exception."""
from app.exceptions.base import RegistryError


class GroupMismatchError(RegistryError):
    """Raised when an item's metadata group doesn't match its directory location."""
    
    def __init__(self, item_id: str, item_type: str, directory_group: str, metadata_group: str, path: str):
        """
        Args:
            item_id: ID of the item (template_id, fragment_id, style_id)
            item_type: Type of item (template, fragment, style)
            directory_group: Expected group from directory structure
            metadata_group: Group declared in metadata
            path: File path where the mismatch was detected
        """
        message = (
            f"{item_type.capitalize()} '{item_id}' in directory '{path}' declares group '{metadata_group}' "
            f"but is located in '{directory_group}/' directory. "
            f"Metadata group must match directory location. Expected group: '{directory_group}'."
        )
        super().__init__(message)
