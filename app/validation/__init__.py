"""Validation module for document generation system.

Note: The Validator class has been removed as it was unused.
Real validation happens via:
- Pydantic models (automatic validation)
- SessionManager.validate_parameters() (template/fragment parameter validation)
- Schema validation in template/fragment registries
"""

from app.validation.error import ValidationError
from app.styles.style_metadata import StyleMetadata
from app.styles.style_list_item import StyleListItem

__all__ = [
    "ValidationError",
    "StyleMetadata",
    "StyleListItem",
]
