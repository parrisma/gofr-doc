"""Template registry system for managing document templates."""
from typing import Dict, List, Optional

from app.registries.base import BaseRegistry
from app.validation.document_models import (
    TemplateSchema,
    TemplateMetadata,
    ParameterSchema,
    FragmentSchema,
    TemplateListItem,
    TemplateDetailsOutput,
)
from app.logger import Logger
from app.exceptions import TemplateNotFoundError, GroupMismatchError


class TemplateRegistry(BaseRegistry):
    """Manages loading, validation, and discovery of document templates."""

    def __init__(self, templates_dir: str, logger: Logger, 
                 group: Optional[str] = None, 
                 groups: Optional[List[str]] = None):
        """
        Initialize the template registry.

        Args:
            templates_dir: Path to directory containing template definitions
            logger: Logger instance
            group: Single group to load (e.g., "public")
            groups: Multiple groups to load (e.g., ["public", "research"])
        """
        self._templates: Dict[str, TemplateSchema] = {}
        super().__init__(templates_dir, logger, group, groups)

    def _get_registry_type(self) -> str:
        """Get registry type for migration."""
        return "templates"

    def _load_items(self) -> None:
        """Load all templates from all configured groups."""
        for group in self.groups:
            self._load_group_items(group)

    def _load_group_items(self, group: str) -> None:
        """Load templates from a specific group directory."""
        group_dir = self.registry_dir / group
        
        if not group_dir.exists():
            self.logger.warning(f"Group directory not found: {group_dir}")
            return
        
        # Load each template directory in the group
        for template_dir in group_dir.iterdir():
            if not template_dir.is_dir():
                continue

            schema_file = template_dir / "template.yaml"
            if not schema_file.exists():
                self.logger.warning(
                    f"Skipping {template_dir.name}: no template.yaml found"
                )
                continue

            try:
                schema_data = self._load_yaml_file(schema_file)
                if not schema_data:
                    continue

                # Convert nested dicts to dataclass instances
                template_schema = self._build_template_schema(schema_data)
                template_id = template_schema.metadata.template_id
                
                # Validate group/directory match
                self._validate_group_match(
                    expected_group=group,
                    actual_group=template_schema.metadata.group,
                    item_id=template_id,
                    item_type="template",
                    file_path=str(schema_file)
                )

                self._templates[template_id] = template_schema
                self.logger.info(
                    f"Loaded template: {template_id} from group '{group}' ({template_schema.metadata.name})"
                )

            except GroupMismatchError as e:
                self.logger.error(f"Group mismatch in {template_dir.name}: {e}")
            except Exception as e:
                self.logger.error(
                    f"Failed to load template from {template_dir.name}: {e}"
                )

    def _build_template_schema(self, data: dict) -> TemplateSchema:
        """Build a TemplateSchema from loaded YAML data."""
        # Build metadata
        metadata_data = data.get("metadata", {})
        metadata = TemplateMetadata(**metadata_data)
        
        # Build global parameters
        global_params = []
        for param_data in data.get("global_parameters", []):
            global_params.append(ParameterSchema(**param_data))
        
        # Build fragments - these are references within the template
        # They don't have a separate group; they inherit the template's group
        fragments = []
        for frag_data in data.get("fragments", []):
            params = []
            for param_data in frag_data.get("parameters", []):
                params.append(ParameterSchema(**param_data))
            frag_data_copy = frag_data.copy()
            frag_data_copy["parameters"] = params
            # Add group from template metadata (embedded fragments inherit template group)
            frag_data_copy["group"] = metadata.group
            fragments.append(FragmentSchema(**frag_data_copy))
        
        return TemplateSchema(
            metadata=metadata,
            global_parameters=global_params,
            fragments=fragments
        )

    def list_templates(self, group: Optional[str] = None) -> List[TemplateListItem]:
        """
        Get a list of available templates.
        
        Args:
            group: Filter by specific group (None = all loaded groups)
        """
        if group:
            if group not in self.groups:
                return []
            # Filter by group
            items = [
                TemplateListItem(
                    template_id=schema.metadata.template_id,
                    name=schema.metadata.name,
                    description=schema.metadata.description,
                    group=schema.metadata.group,
                )
                for schema in self._templates.values()
                if schema.metadata.group == group
            ]
        else:
            # All loaded groups
            items = [
                TemplateListItem(
                    template_id=schema.metadata.template_id,
                    name=schema.metadata.name,
                    description=schema.metadata.description,
                    group=schema.metadata.group,
                )
                for schema in self._templates.values()
            ]
        return items

    def get_items_by_group(self) -> Dict[str, List[TemplateListItem]]:
        """Get all templates organized by group."""
        result = {group: [] for group in self.groups}
        for schema in self._templates.values():
            item = TemplateListItem(
                template_id=schema.metadata.template_id,
                name=schema.metadata.name,
                description=schema.metadata.description,
                group=schema.metadata.group,
            )
            result[schema.metadata.group].append(item)
        return result

    def get_template_schema(self, template_id: str) -> Optional[TemplateSchema]:
        """Get the full schema for a template."""
        return self._templates.get(template_id)

    def get_template_details(self, template_id: str) -> Optional[TemplateDetailsOutput]:
        """Get template details including global parameters."""
        schema = self._templates.get(template_id)
        if not schema:
            return None

        return TemplateDetailsOutput(
            template_id=schema.metadata.template_id,
            name=schema.metadata.name,
            description=schema.metadata.description,
            group=schema.metadata.group,
            global_parameters=schema.global_parameters,
        )

    def get_fragment_schema(
        self, template_id: str, fragment_id: str
    ) -> Optional[FragmentSchema]:
        """Get the schema for a specific fragment within a template."""
        schema = self._templates.get(template_id)
        if not schema:
            return None

        for fragment in schema.fragments:
            if fragment.fragment_id == fragment_id:
                return fragment

        return None

    def template_exists(self, template_id: str) -> bool:
        """Check if a template exists."""
        return template_id in self._templates

    def get_jinja_template(self, template_id: str, template_file: str):
        """
        Get a Jinja2 template for rendering.

        Args:
            template_id: The template identifier
            template_file: The template file name (e.g., 'document.html.jinja2')

        Returns:
            Jinja2 Template object

        Raises:
            TemplateNotFound: If template file doesn't exist
        """
        schema = self._templates.get(template_id)
        if not schema:
            raise TemplateNotFoundError(template_id)
        
        # Template files are in: templates/{group}/{template_id}/{template_file}
        group = schema.metadata.group
        template_path = f"{group}/{template_id}/{template_file}"
        return self._get_jinja_template(template_path)

    def validate_global_parameters(
        self, template_id: str, parameters: Dict
    ) -> tuple[bool, List[str]]:
        """
        Validate global parameters against template schema.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        schema = self._templates.get(template_id)
        if not schema:
            return False, [f"Template '{template_id}' not found"]

        return self._validate_parameters_against_schema(
            parameters=parameters,
            parameter_schemas=schema.global_parameters,
            context=f"template '{template_id}'"
        )

    def validate_fragment_parameters(
        self, template_id: str, fragment_id: str, parameters: Dict
    ) -> tuple[bool, List[str]]:
        """
        Validate fragment parameters against schema.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        fragment_schema = self.get_fragment_schema(template_id, fragment_id)
        if not fragment_schema:
            return False, [
                f"Fragment '{fragment_id}' not found in template '{template_id}'"
            ]

        # Use common validation logic
        is_valid, errors = self._validate_parameters_against_schema(
            parameters=parameters,
            parameter_schemas=fragment_schema.parameters,
            context=f"fragment '{fragment_id}' in template '{template_id}'"
        )

        # Fragment-specific validation
        if fragment_id == "table":
            from app.validation.table_validator import validate_table_data, TableValidationError
            try:
                validate_table_data(parameters)
            except TableValidationError as e:
                errors.append(str(e))
                is_valid = False

        return is_valid, errors
