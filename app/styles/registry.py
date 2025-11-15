"""Style registry system for managing document styles (CSS)."""
import os
import yaml
from typing import Dict, List, Optional
from pathlib import Path

from app.styles.models import StyleMetadata, StyleListItem
from app.logger import Logger


class StyleRegistry:
    """Manages loading and discovery of document styles."""

    def __init__(self, styles_dir: str, logger: Logger):
        """
        Initialize the style registry.

        Args:
            styles_dir: Path to directory containing style definitions
            logger: Logger instance
        """
        self.styles_dir = Path(styles_dir)
        self.logger = logger
        self._styles: Dict[str, StyleMetadata] = {}
        self._css_content: Dict[str, str] = {}
        self._default_style_id: Optional[str] = None
        self._load_styles()

    def _load_styles(self) -> None:
        """Load all styles from the styles directory."""
        if not self.styles_dir.exists():
            self.logger.error(f"Styles directory not found: {self.styles_dir}")
            return

        # Load each style directory
        for style_dir in self.styles_dir.iterdir():
            if not style_dir.is_dir():
                continue

            metadata_file = style_dir / "style.yaml"
            css_file = style_dir / "style.css"

            if not metadata_file.exists() or not css_file.exists():
                self.logger.warning(
                    f"Skipping {style_dir.name}: missing style.yaml or style.css"
                )
                continue

            try:
                # Load metadata
                with open(metadata_file, "r") as f:
                    metadata_data = yaml.safe_load(f)

                style_metadata = StyleMetadata(**metadata_data)
                style_id = style_metadata.style_id

                # Load CSS content
                with open(css_file, "r") as f:
                    css_content = f.read()

                self._styles[style_id] = style_metadata
                self._css_content[style_id] = css_content

                # Set first style as default if none set
                if self._default_style_id is None:
                    self._default_style_id = style_id
                    self.logger.info(f"Set default style: {style_id}")

                self.logger.info(
                    f"Loaded style: {style_id} ({style_metadata.name})"
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to load style from {style_dir.name}: {e}"
                )

    def list_styles(self) -> List[StyleListItem]:
        """Get a list of all available styles."""
        return [
            StyleListItem(
                style_id=metadata.style_id,
                name=metadata.name,
                description=metadata.description,
            )
            for metadata in self._styles.values()
        ]

    def get_style_metadata(self, style_id: str) -> Optional[StyleMetadata]:
        """Get metadata for a style."""
        return self._styles.get(style_id)

    def get_style_css(self, style_id: str) -> Optional[str]:
        """Get CSS content for a style."""
        return self._css_content.get(style_id)

    def style_exists(self, style_id: str) -> bool:
        """Check if a style exists."""
        return style_id in self._styles

    def get_default_style_id(self) -> Optional[str]:
        """Get the default style ID."""
        return self._default_style_id

    def get_default_css(self) -> str:
        """Get the CSS for the default style."""
        if self._default_style_id:
            return self._css_content.get(self._default_style_id, "")
        return ""
