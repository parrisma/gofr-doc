"""Base registry for template and fragment management."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, List
from jinja2 import Environment, FileSystemLoader, select_autoescape
import yaml
from app.logger import Logger


class BaseRegistry(ABC):
    """Abstract base for registries managing schema + Jinja2 templates."""

    def __init__(self, registry_dir: str, logger: Logger, 
                 group: Optional[str] = None, 
                 groups: Optional[List[str]] = None):
        """
        Initialize the registry.

        Args:
            registry_dir: Path to directory containing definitions
            logger: Logger instance
            group: Single group to load (e.g., "public")
            groups: Multiple groups to load (e.g., ["public", "research"])
        """
        self.registry_dir = Path(registry_dir)
        self.logger = logger
        
        # Determine which groups to load
        self.groups = self._resolve_groups(group, groups)
        
        self._jinja_env: Optional[Environment] = None
        self._setup_jinja_env()
        self._load_items()

    def _get_registry_type(self) -> str:
        """Get registry type (templates, fragments, or styles). Override in subclasses."""
        return "templates"

    def _resolve_groups(self, group: Optional[str], groups: Optional[List[str]]) -> List[str]:
        """
        Determine which groups to load.
        
        Priority:
        1. If groups parameter provided, use it
        2. If group parameter provided, use single group
        3. Otherwise, discover all groups in directory
        """
        if groups:
            return groups
        if group:
            return [group]
        return self._discover_groups()

    def _discover_groups(self) -> List[str]:
        """
        Find all group directories in registry.
        
        Groups are directories at root level that don't start with underscore.
        """
        if not self.registry_dir.exists():
            self.logger.warning(f"Registry directory does not exist: {self.registry_dir}")
            return ["public"]
        
        groups = []
        try:
            for item in self.registry_dir.iterdir():
                if item.is_dir() and not item.name.startswith('_'):
                    groups.append(item.name)
        except Exception as e:
            self.logger.error(f"Failed to discover groups in {self.registry_dir}: {e}")
            return ["public"]
        
        return sorted(groups) if groups else ["public"]

    def _setup_jinja_env(self) -> None:
        """Setup Jinja2 environment for template rendering."""
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(self.registry_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def list_groups(self) -> List[str]:
        """Return list of loaded groups."""
        return self.groups

    def get_items_by_group(self) -> Dict[str, List]:
        """
        Get all items organized by group.
        
        Subclasses should override to populate with their items.
        """
        return {group: [] for group in self.groups}

    @abstractmethod
    def _load_items(self) -> None:
        """Load all items from registry directory. Implemented by subclasses."""
        pass

    def _load_yaml_file(self, file_path: Path) -> Optional[Dict]:
        """Load and parse a YAML file."""
        try:
            with open(file_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to parse YAML {file_path}: {e}")
            return None

    def _validate_group_match(self, expected_group: str, actual_group: str, 
                            item_id: str, item_type: str, file_path: str) -> None:
        """
        Validate that item's declared group matches its directory location.
        
        Args:
            expected_group: Group from directory structure
            actual_group: Group declared in metadata
            item_id: ID of the item
            item_type: Type of item (template, fragment, style)
            file_path: Path to the item file
            
        Raises:
            GroupMismatchError if mismatch detected
        """
        from app.exceptions import GroupMismatchError
        
        if expected_group != actual_group:
            raise GroupMismatchError(
                item_id=item_id,
                item_type=item_type,
                directory_group=expected_group,
                metadata_group=actual_group,
                path=file_path
            )

    def _get_jinja_template(self, template_path: str):
        """
        Get a Jinja2 template for rendering.

        Args:
            template_path: Path relative to registry_dir

        Returns:
            Jinja2 Template object
        """
        if self._jinja_env is None:
            raise RuntimeError("Jinja environment not initialized")
        return self._jinja_env.get_template(template_path)
