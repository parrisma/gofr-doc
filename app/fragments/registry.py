"""Fragment registry system for managing reusable content fragments."""
from typing import Dict, List, Optional

from app.registry_base import BaseRegistry
from app.validation.document_models import FragmentSchema, ParameterSchema
from app.logger import Logger
from app.exceptions import FragmentNotFoundError, GroupMismatchError


class FragmentRegistry(BaseRegistry):
    """Manages loading, validation, and discovery of reusable fragments."""

    def __init__(self, fragments_dir: str, logger: Logger,
                 group: Optional[str] = None,
                 groups: Optional[List[str]] = None):
        """
        Initialize the fragment registry.

        Args:
            fragments_dir: Path to directory containing fragment definitions
            logger: Logger instance
            group: Single group to load (e.g., "public")
            groups: Multiple groups to load (e.g., ["public", "research"])
        """
        self._fragments: Dict[str, FragmentSchema] = {}
        super().__init__(fragments_dir, logger, group, groups)

    def _get_registry_type(self) -> str:
        """Get registry type for migration."""
        return "fragments"

    def _load_items(self) -> None:
        """Load all fragments from all configured groups."""
        for group in self.groups:
            self._load_group_items(group)

    def _load_group_items(self, group: str) -> None:
        """Load fragments from a specific group directory."""
        group_dir = self.registry_dir / group
        
        if not group_dir.exists():
            self.logger.warning(f"Group directory not found: {group_dir}")
            return

        # Load each fragment directory in the group
        for fragment_dir in group_dir.iterdir():
            if not fragment_dir.is_dir():
                continue

            schema_file = fragment_dir / "fragment.yaml"
            if not schema_file.exists():
                self.logger.debug(
                    f"Skipping {fragment_dir.name}: no fragment.yaml found"
                )
                continue

            try:
                schema_data = self._load_yaml_file(schema_file)
                if not schema_data:
                    continue

                # Convert nested dicts to dataclass instances
                fragment_schema = self._build_fragment_schema(schema_data)
                fragment_id = fragment_schema.fragment_id
                
                # Validate group/directory match
                self._validate_group_match(
                    expected_group=group,
                    actual_group=fragment_schema.group,
                    item_id=fragment_id,
                    item_type="fragment",
                    file_path=str(schema_file)
                )

                self._fragments[fragment_id] = fragment_schema
                self.logger.info(
                    f"Loaded fragment: {fragment_id} from group '{group}' ({fragment_schema.name})"
                )

            except GroupMismatchError as e:
                self.logger.error(f"Group mismatch in {fragment_dir.name}: {e}")
            except Exception as e:
                self.logger.error(
                    f"Failed to load fragment from {fragment_dir.name}: {e}"
                )

    def _build_fragment_schema(self, data: dict) -> FragmentSchema:
        """Build a FragmentSchema from loaded YAML data."""
        
        # Build parameters
        params = []
        for param_data in data.get("parameters", []):
            params.append(ParameterSchema(**param_data))
        
        return FragmentSchema(
            fragment_id=data.get("fragment_id", ""),
            group=data.get("group", "public"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            parameters=params
        )

    def list_fragments(self, group: Optional[str] = None) -> List[dict]:
        """
        Get a list of available fragments.
        
        Args:
            group: Filter by specific group (None = all loaded groups)
        """
        if group:
            if group not in self.groups:
                return []
            # Filter by group
            items = [
                {
                    "fragment_id": schema.fragment_id,
                    "name": schema.name,
                    "description": schema.description,
                    "group": schema.group,
                    "parameter_count": len(schema.parameters),
                }
                for schema in self._fragments.values()
                if schema.group == group
            ]
        else:
            # All loaded groups
            items = [
                {
                    "fragment_id": schema.fragment_id,
                    "name": schema.name,
                    "description": schema.description,
                    "group": schema.group,
                    "parameter_count": len(schema.parameters),
                }
                for schema in self._fragments.values()
            ]
        return items

    def get_items_by_group(self) -> Dict[str, List[dict]]:
        """Get all fragments organized by group."""
        result = {group: [] for group in self.groups}
        for schema in self._fragments.values():
            item = {
                "fragment_id": schema.fragment_id,
                "name": schema.name,
                "description": schema.description,
                "group": schema.group,
                "parameter_count": len(schema.parameters),
            }
            result[schema.group].append(item)
        return result

    def get_fragment_schema(self, fragment_id: str) -> Optional[FragmentSchema]:
        """Get the full schema for a fragment."""
        return self._fragments.get(fragment_id)

    def fragment_exists(self, fragment_id: str) -> bool:
        """Check if a fragment exists."""
        return fragment_id in self._fragments

    def get_jinja_template(self, fragment_id: str):
        """Get the Jinja2 template for rendering a fragment."""
        schema = self._fragments.get(fragment_id)
        if not schema:
            available = [s.fragment_id for s in self._fragments.values()]
            raise FragmentNotFoundError(
                fragment_id=fragment_id,
                template_id="unknown",
                group=schema.group if schema else "unknown",
                available_fragments=available
            )
        
        # Fragment files are in: fragments/{group}/{fragment_id}/fragment.html.jinja2
        group = schema.group
        return self._get_jinja_template(f"{group}/{fragment_id}/fragment.html.jinja2")

    def validate_parameters(
        self, fragment_id: str, parameters: Dict
    ) -> tuple[bool, List[str]]:
        """
        Validate fragment parameters against schema.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        fragment_schema = self._fragments.get(fragment_id)
        if not fragment_schema:
            return False, [f"Fragment '{fragment_id}' not found"]

        errors = []
        provided_params = set(parameters.keys())

        # Check required parameters
        for param_schema in fragment_schema.parameters:
            if param_schema.required and param_schema.name not in parameters:
                errors.append(
                    f"Missing required parameter '{param_schema.name}' "
                    f"({param_schema.description})"
                )

        # Check for unexpected parameters
        expected_params = {p.name for p in fragment_schema.parameters}
        unexpected = provided_params - expected_params
        if unexpected:
            errors.append(
                f"Unexpected parameters: {', '.join(unexpected)}. "
                f"Expected: {', '.join(expected_params)}"
            )

        return len(errors) == 0, errors
