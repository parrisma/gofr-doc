"""Template registry system for managing document templates."""
import os
import yaml
from typing import Dict, List, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound

from app.validation.document_models import (
    TemplateSchema,
    TemplateMetadata,
    ParameterSchema,
    FragmentSchema,
    TemplateListItem,
    TemplateDetailsOutput,
)
from app.logger import Logger


class TemplateRegistry:
    """Manages loading, validation, and discovery of document templates."""

    def __init__(self, templates_dir: str, logger: Logger):
        """
        Initialize the template registry.

        Args:
            templates_dir: Path to directory containing template definitions
            logger: Logger instance
        """
        self.templates_dir = Path(templates_dir)
        self.logger = logger
        self._templates: Dict[str, TemplateSchema] = {}
        self._jinja_env: Optional[Environment] = None
        self._load_templates()

    def _load_templates(self) -> None:
        """Load all templates from the templates directory."""
        if not self.templates_dir.exists():
            self.logger.error(f"Templates directory not found: {self.templates_dir}")
            return

        # Setup Jinja2 environment
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Load each template directory
        for template_dir in self.templates_dir.iterdir():
            if not template_dir.is_dir():
                continue

            schema_file = template_dir / "template.yaml"
            if not schema_file.exists():
                self.logger.warning(
                    f"Skipping {template_dir.name}: no template.yaml found"
                )
                continue

            try:
                with open(schema_file, "r") as f:
                    schema_data = yaml.safe_load(f)

                template_schema = TemplateSchema(**schema_data)
                template_id = template_schema.metadata.template_id

                self._templates[template_id] = template_schema
                self.logger.info(
                    f"Loaded template: {template_id} ({template_schema.metadata.name})"
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to load template from {template_dir.name}: {e}"
                )

    def list_templates(self) -> List[TemplateListItem]:
        """Get a list of all available templates."""
        return [
            TemplateListItem(
                template_id=schema.metadata.template_id,
                name=schema.metadata.name,
                description=schema.metadata.description,
            )
            for schema in self._templates.values()
        ]

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
        if self._jinja_env is None:
            raise RuntimeError("Jinja environment not initialized")

        # Template files are in: templates/{template_id}/{template_file}
        template_path = f"{template_id}/{template_file}"
        return self._jinja_env.get_template(template_path)

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

        errors = []
        provided_params = set(parameters.keys())
        
        # Check required parameters
        for param_schema in schema.global_parameters:
            if param_schema.required and param_schema.name not in parameters:
                errors.append(
                    f"Missing required parameter '{param_schema.name}' "
                    f"({param_schema.description})"
                )

        # Check for unexpected parameters
        expected_params = {p.name for p in schema.global_parameters}
        unexpected = provided_params - expected_params
        if unexpected:
            errors.append(
                f"Unexpected parameters: {', '.join(unexpected)}. "
                f"Expected: {', '.join(expected_params)}"
            )

        return len(errors) == 0, errors

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
