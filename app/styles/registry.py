"""Style registry system for managing document styles (CSS)."""

import yaml
from typing import Dict, List, Optional

from app.registries.base import BaseRegistry
from app.styles.style_metadata import StyleMetadata
from app.styles.style_list_item import StyleListItem
from app.logger import Logger
from app.exceptions import GroupMismatchError


class StyleRegistry(BaseRegistry):
    """Manages loading and discovery of document styles."""

    def __init__(
        self,
        styles_dir: str,
        logger: Logger,
        group: Optional[str] = None,
        groups: Optional[List[str]] = None,
    ):
        """
        Initialize the style registry.

        Args:
            styles_dir: Path to directory containing style definitions
            logger: Logger instance
            group: Single group to load (e.g., "public")
            groups: Multiple groups to load (e.g., ["public", "research"])
        """
        self._styles: Dict[str, StyleMetadata] = {}
        self._css_content: Dict[str, str] = {}
        self._default_style_id: Optional[str] = None
        super().__init__(styles_dir, logger, group, groups)

    def _get_registry_type(self) -> str:
        """Get registry type for migration."""
        return "styles"

    def _load_items(self) -> None:
        """Load all styles from all configured groups."""
        for group in self.groups:
            self._load_group_items(group)

    def _load_group_items(self, group: str) -> None:
        """Load styles from a specific group directory."""
        group_dir = self.registry_dir / group

        if not group_dir.exists():
            self.logger.warning(f"Group directory not found: {group_dir}")
            return

        # Load each style directory in the group
        for style_dir in group_dir.iterdir():
            if not style_dir.is_dir():
                continue

            metadata_file = style_dir / "style.yaml"
            css_file = style_dir / "style.css"

            if not metadata_file.exists() or not css_file.exists():
                self.logger.warning(f"Skipping {style_dir.name}: missing style.yaml or style.css")
                continue

            try:
                # Load metadata
                with open(metadata_file, "r") as f:
                    metadata_data = yaml.safe_load(f)

                style_metadata = StyleMetadata(**metadata_data)
                style_id = style_metadata.style_id

                # Validate group/directory match
                self._validate_group_match(
                    expected_group=group,
                    actual_group=style_metadata.group,
                    item_id=style_id,
                    item_type="style",
                    file_path=str(metadata_file),
                )

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
                    f"Loaded style: {style_id} from group '{group}' ({style_metadata.name})"
                )

            except GroupMismatchError as e:
                self.logger.error(f"Group mismatch in {style_dir.name}: {e}")
            except Exception as e:
                self.logger.error(f"Failed to load style from {style_dir.name}: {e}")

    def list_styles(self, group: Optional[str] = None) -> List[StyleListItem]:
        """
        Get a list of available styles.

        Args:
            group: Filter by specific group (None = all loaded groups)
        """
        if group:
            if group not in self.groups:
                return []
            # Filter by group
            items = [
                StyleListItem(
                    style_id=metadata.style_id,
                    name=metadata.name,
                    description=metadata.description,
                    group=metadata.group,
                )
                for metadata in self._styles.values()
                if metadata.group == group
            ]
        else:
            # All loaded groups
            items = [
                StyleListItem(
                    style_id=metadata.style_id,
                    name=metadata.name,
                    description=metadata.description,
                    group=metadata.group,
                )
                for metadata in self._styles.values()
            ]
        return items

    def get_items_by_group(self) -> Dict[str, List[StyleListItem]]:
        """Get all styles organized by group."""
        result = {group: [] for group in self.groups}
        for metadata in self._styles.values():
            item = StyleListItem(
                style_id=metadata.style_id,
                name=metadata.name,
                description=metadata.description,
                group=metadata.group,
            )
            result[metadata.group].append(item)
        return result

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
