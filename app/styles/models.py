"""Data models for style metadata and list items."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StyleMetadata:
    """Metadata for a style loaded from style.yaml."""
    style_id: str
    name: str
    description: str
    version: str = "1.0.0"


@dataclass
class StyleListItem:
    """A summary item for listing available styles."""
    style_id: str
    name: str
    description: str
