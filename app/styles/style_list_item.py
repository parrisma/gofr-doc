"""Style list item model for style discovery."""

from pydantic import BaseModel


class StyleListItem(BaseModel):
    """A summary item for listing available styles."""

    style_id: str
    name: str
    description: str
    group: str  # Mandatory - comes from loaded style metadata
