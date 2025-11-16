"""Style metadata model loaded from style.yaml."""
from dataclasses import dataclass


@dataclass
class StyleMetadata:
    """Metadata for a style loaded from style.yaml."""
    style_id: str
    group: str  # NEW: Mandatory group field (must match directory location)
    name: str
    description: str
    version: str = "1.0.0"
