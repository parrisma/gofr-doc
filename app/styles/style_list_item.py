"""Style list item model for style discovery."""
from dataclasses import dataclass


@dataclass
class StyleListItem:
    """A summary item for listing available styles."""
    style_id: str
    name: str
    description: str
    group: str  # Mandatory - comes from loaded style metadata
