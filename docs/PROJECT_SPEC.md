# Document Generation MCP Service Specification

> **Related Documentation:**
> - [← Back to README](../README.md#-documentation) | [Development Guide](DEVELOPMENT.md) | [Configuration](../app/config_docs.py)
> - **Implementation**: [Document Generation](DOCUMENT_GENERATION.md) | [Data Persistence](DATA_PERSISTENCE.md) | [Rendering](RENDERING_README.md)
> - **Features**: [Features Guide](FEATURES.md)
> - **Deployment**: [Docker](DOCKER.md) | [Authentication](AUTHENTICATION.md)

## 1. Project Overview

- **Objective**: Deliver a stateful, discoverable, and type-safe Document Generation API with group-based multi-tenant security, exposed to agentic LLM clients via the Model Context Protocol (MCP).
- **Workflow**: LLM follows a Think → Act → Observe loop across discovery, session management, iterative content assembly, rendering, and explicit cleanup, all within a secure group context.
- **Quality Goals**: Minimal, production-ready async Python with strong validation, multi-tenant isolation, maintainability, performance, observability, and persistence across restarts.
- **Context**: Replaces the earlier graph MCP server while retaining shared subsystems (auth, storage, logging) and introducing document-centric components with group-based security.

## 2. Technology Stack & Architecture

| Component | Technology | Notes |
|-----------|------------|-------|
| Protocol | `mcp>=0.9.0` | Primary integration surface for LLM agents |
| Web Framework | FastAPI (async) | Hosts MCP transport endpoints with minimal glue |
| Validation | Pydantic v2 | Universal schema enforcement for inputs/outputs |
| Templates | Pydantic schema + Jinja2 rendering | Type-safe parameters with flexible HTML templating |
| Styles | HTML + CSS (Jinja2 + static CSS files) | Stylesheet layer independent of template structure |
| Rendering | HTML base → WeasyPrint (PDF) → html2text (Markdown) | HTML is canonical representation |
| Storage | Existing persistent storage (`app/storage`) | Sessions survive process restarts; group-scoped directories |
| Logging | Existing structured logger (`app/logger`) | Consistent, contextual diagnostics |
| Auth | JWT with group claims | Multi-tenant isolation via group extraction from token |
| Security | Group-based access control | Session ownership verification, directory isolation per group |

### Key Directories

```text
app/
  templates/        # Template registry + loaders
  styles/           # Style registry and CSS helpers
  fragments/        # Fragment helper utilities (reserved)
  sessions/         # Session manager and persistence logic
  rendering/        # Rendering engine and converters
  validation/       # Pydantic schemas and validation helpers
templates/          # Static template bundles (YAML + Jinja2)
styles/             # Static style bundles (style.yaml + style.css)
```

## 3. Template & Fragment System

- **Definition Approach**: `TemplateSchema` (Pydantic) captures metadata, global parameters, and fragment schemas; YAML files provide data, Jinja2 renders HTML.
- **Structure Example**: `templates/basic_report/{template.yaml, document.html.jinja2, fragments/paragraph.html.jinja2}`.
- **Parameter Types**: Enumerated (`string`, `integer`, `number`, `boolean`, `array`, `object`) with descriptions, required flags, defaults, and examples.
- **Fragment Instances**: `add_fragment` generates UUID4 `fragment_instance_guid`, persisted with parameters and timestamps.
- **Ordering**: Fragments append by default; `position` supports `start`, `end`, `before:<guid>`, or `after:<guid>`.
- **Removal**: `remove_fragment` deletes a fragment instance; all fragment GUIDs purged on session abort.
- **Inspection**: `list_session_fragments` reveals ordered fragment metadata for LLM observability and re-planning.

## 4. Style System

- **Independence**: Styles parallel CSS—decoupled from templates, linked by shared element names.
- **Assets**: Each style bundle contains `style.yaml` (metadata) and `style.css` (complete stylesheet).
- **Defaults**: First successfully loaded style becomes default; callers may override via `style_id` during render.
- **Reuse**: Styles apply uniformly across HTML, PDF, and Markdown outputs.

## 5. Session Lifecycle & Persistence

1. **Create**: `create_document_session` locks template for the session and binds it to the caller's group.
2. **Iterate**: `set_global_parameters` (overwritable), `add_fragment`, `remove_fragment`, `list_session_fragments`—all verified against session ownership.
3. **Render**: `get_document` supports repeated renders (`html`, `pdf`, `md`) with optional style selection; must follow successful `set_global_parameters`.
4. **Cleanup**: `abort_document_session` deletes session data from persistent storage and validates group ownership.

### Persistence & Security

- Sessions stored with key prefix `session:<group>:<uuid>` via `app/storage` and persist across restarts.
- Each session is bound to a group extracted from the JWT token's `group` claim.
- Fragment GUIDs scoped to their session, automatically cleaned on abort.
- Session metadata records creation, update timestamps, and group context for observability and enforcement.
- All session operations verify caller's group matches session's group; cross-group access is denied with `SESSION_NOT_FOUND`.
- In non-authentication mode (development), all sessions default to the `public` group.

### Concurrency & Access

- Async session manager enables concurrent operations while relying on storage guarantees.
- Multiple agents may coordinate on a session using fragment GUIDs for deterministic updates.
- Group isolation prevents accidental or malicious cross-tenant access.

## 6. Security Model

### Authentication & Group Binding

- **JWT Tokens**: Clients provide JWT tokens via HTTP `Authorization: Bearer <token>` header in MCP server mode, or via environment configuration in development.
- **Group Extraction**: On each request, the auth service extracts the `group` claim from the JWT payload.
- **Session Ownership**: Sessions are created with and bound to the caller's group. All subsequent operations (`set_global_parameters`, `add_fragment`, `remove_fragment`, `list_session_fragments`, `get_document`, `abort_document_session`) verify that the caller's group matches the session's group.
- **Access Denial**: If group mismatch detected, the session is treated as non-existent (`SESSION_NOT_FOUND`), preventing information leakage.

### Non-Authentication Mode

- **Development Workflow**: When authentication is disabled (no `DOCO_AUTH_SERVICE_URL` or equivalent), all operations default to the `public` group.
- **Use Case**: Local development, testing, and single-tenant deployments without auth infrastructure.
- **Behavior**: Discovery tools (templates, styles) remain unrestricted; all sessions created default to `public` and are accessible only in non-auth context.

### Directory Isolation

- **Storage**: Group context is encoded in storage key prefixes (`session:<group>:<uuid>`, etc.), enabling future per-group filesystem isolation.
- **Data**: Sessions and artifacts (fragments, rendered documents) are logically partitioned by group and inaccessible to other groups.

## 7. Tool Surface (Source of Truth)

## 7. Tool Surface (Source of Truth)

```text
# Discovery Tools (no authentication required)
ping
list_templates
get_template_details
list_template_fragments
get_fragment_details
list_styles

# Session Tools (require valid JWT with group claim or no-auth mode)
create_document_session       # Binds session to caller's group
set_global_parameters        # Verifies session ownership
add_fragment                  # Verifies session ownership
remove_fragment               # Verifies session ownership
list_session_fragments        # Verifies session ownership
abort_document_session        # Verifies session ownership
get_document                  # Verifies session ownership
```

- `add_fragment` returns `fragment_instance_guid`, insertion index, and confirmation message.
- `get_document` enforces prior global parameter configuration while leaving session active for subsequent renders.
- All session tools validate `session.group == caller.group` before proceeding.
- Pydantic models mirror tool I/O schemas to ensure precise validation and documentation.

## 8. Error Handling & Recovery Guidance

- **MCP Responses**: Structured `ErrorResponse` with `error_code`, `message`, contextual `details`, and actionable `recovery_strategy`.
- **Web API**: HTTP status codes plus mirrored descriptive payloads for human operators.
- **Validation Coverage**: Missing/extra parameters, invalid IDs, ordering references to unknown GUIDs, unset global parameters on render, unsupported formats or styles, cross-group access attempts.
- **Security Errors**: Mismatched group claims return `SESSION_NOT_FOUND` (rather than explicit "access denied") to prevent information leakage.
- **Example Strategy**: "Call set_global_parameters with required fields before invoking get_document" or "Ensure your JWT token contains a valid 'group' claim."

## 9. Rendering Pipeline

1. **HTML Generation**: Template registry renders `document.html.jinja2`, injecting global parameters, ordered fragment HTML, and CSS references.
2. **PDF Conversion**: WeasyPrint converts HTML to PDF, returning base64-encoded data for transport.
3. **Markdown Conversion**: html2text translates HTML to Markdown with preserved links, images, and unclamped line widths.

## 10. Reuse & Integration Plan

- **Reuse**: `auth`, `storage`, `logger`, `config` modules remain intact.
- **Replace/Update**: `app/mcp_server.py` and related entry points transition to document tooling.
- **New Components**: Template/style registries, session manager, rendering engine, expanded validation schemas.
- **Testing**: End-to-end flow tests plus targeted validation/error-path coverage; persistence validated through restart scenarios.

## 11. Resolved Design Decisions

- ✅ Hybrid Pydantic schema + Jinja2 templating for templates.
- ✅ UUID4 fragment instance GUIDs returned by `add_fragment`.
- ✅ Dedicated `list_session_fragments` and `remove_fragment` tools.
- ✅ HTML as canonical format, with WeasyPrint (PDF) and html2text (Markdown) conversions.
- ✅ Styles defined independently via CSS bundles.
- ✅ Readable slugs for templates/fragments/styles; UUID4 for sessions/fragment instances.
- ✅ Descriptive MCP errors with recovery actions; HTTP responses for web surface.
- ✅ Sessions persisted via existing storage service.
- ✅ **Group-based multi-tenant security**: Sessions bound to JWT group claim with cross-group access denial.
- ✅ **Dual-mode operation**: Production auth mode (JWT with groups) and development no-auth mode (public group default).

## 12. Implementation Roadmap

1. Implement MCP tool handlers leveraging new registries, session manager, and rendering engine, with group-based security verification.
2. Populate initial templates (e.g., `basic_report`, `technical_doc`) and styles.
3. Develop automated tests spanning discovery → session → construction → rendering → cleanup, including multi-tenant security and group isolation validation.
4. Refresh documentation in `docs/` and related run-books.
5. Verify deployment scripts and Docker assets for new dependencies (Jinja2, WeasyPrint, html2text, PyYAML).

---

**Status**: Specification finalized and updated (Nov 18, 2025) with group-based security model. Core implementation complete with 300/300 tests passing, including 5 security tests and 4 end-to-end workflow tests demonstrating full multi-tenant isolation.
# Fragment Registry Design Proposal

## Overview

This proposal outlines a `FragmentRegistry` that manages fragment templates independently while sharing the technical foundation with `TemplateRegistry`. Both registries load schemas from YAML, manage Jinja2 templates, and provide metadata discovery—but operate at different scopes.

## Key Design Principles

1. **DRY (Don't Repeat Yourself)**: Extract common registry behavior into a shared base class
2. **Single Responsibility**: Templates manage document structure; fragments manage reusable content blocks
3. **Parallel APIs**: Similar method signatures for consistent developer experience
4. **Independent Loading**: Fragments can be loaded from a separate directory tree
5. **Composition**: Fragments are discovered via templates but rendered independently

## Architecture

### Current State
```
TemplateRegistry
├── Loads: templates/{template_id}/template.yaml
├── Manages: TemplateSchema, ParameterSchema, FragmentSchema
└── Renders: Jinja2 templates for documents + fragments
```

### Proposed State
```
BaseRegistry (abstract)
├── _load_from_yaml()
├── _validate_schema()
└── _get_jinja_template()

TemplateRegistry (extends BaseRegistry)
├── Load: templates/{template_id}/template.yaml
├── Manage: TemplateSchema with embedded FragmentSchema refs
├── Render: Document HTML via document.html.jinja2
└── Discover: Global parameters + fragment metadata

FragmentRegistry (extends BaseRegistry)
├── Load: fragments/{fragment_id}/fragment.yaml
├── Manage: FragmentSchema with full details
├── Render: Fragment HTML via fragment.html.jinja2
└── Discover: Fragment parameters + metadata
```

## Implementation Strategy

### 1. Create Base Registry Class

**File:** `app/registry_base.py`

```python
"""Base registry for template and fragment management."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
import yaml
from app.logger import Logger


class BaseRegistry(ABC):
    """Abstract base for registries managing schema + Jinja2 templates."""

    def __init__(self, registry_dir: str, logger: Logger):
        """
        Initialize the registry.
        
        Args:
            registry_dir: Path to directory containing definitions
            logger: Logger instance
        """
        self.registry_dir = Path(registry_dir)
        self.logger = logger
        self._jinja_env: Optional[Environment] = None
        self._setup_jinja_env()
        self._load_items()

    def _setup_jinja_env(self) -> None:
        """Setup Jinja2 environment for template rendering."""
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(self.registry_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

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
```

### 2. Refactor TemplateRegistry to Extend BaseRegistry

**File:** `app/templates/registry.py`

```python
"""Template registry system for managing document templates."""
from typing import Dict, List, Optional
from pathlib import Path

from app.registry_base import BaseRegistry
from app.validation.document_models import (
    TemplateSchema,
    TemplateListItem,
    TemplateDetailsOutput,
    FragmentSchema,
    ParameterSchema,
)
from app.logger import Logger


class TemplateRegistry(BaseRegistry):
    """Manages loading, validation, and discovery of document templates."""

    def __init__(self, templates_dir: str, logger: Logger):
        """
        Initialize the template registry.

        Args:
            templates_dir: Path to directory containing template definitions
            logger: Logger instance
        """
        self._templates: Dict[str, TemplateSchema] = {}
        super().__init__(templates_dir, logger)

    def _load_items(self) -> None:
        """Load all templates from the templates directory."""
        if not self.registry_dir.exists():
            self.logger.error(f"Templates directory not found: {self.registry_dir}")
            return

        # Load each template directory
        for template_dir in self.registry_dir.iterdir():
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

    def get_jinja_template_for_document(self, template_id: str):
        """Get the main document Jinja2 template."""
        return self._get_jinja_template(f"{template_id}/document.html.jinja2")

    def get_jinja_template_for_fragment(self, template_id: str, fragment_id: str):
        """Get a fragment Jinja2 template within a template."""
        return self._get_jinja_template(
            f"{template_id}/fragments/{fragment_id}.html.jinja2"
        )

    def validate_global_parameters(
        self, template_id: str, parameters: Dict
    ) -> tuple[bool, List[str]]:
        """Validate global parameters against template schema."""
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
        """Validate fragment parameters against schema."""
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
```

### 3. Create Standalone FragmentRegistry

**File:** `app/fragments/registry.py`

```python
"""Fragment registry system for managing reusable content fragments."""
from typing import Dict, List, Optional
from pathlib import Path

from app.registry_base import BaseRegistry
from app.validation.document_models import (
    FragmentSchema,
    FragmentListItem,
)
from app.logger import Logger


class FragmentRegistry(BaseRegistry):
    """Manages loading, validation, and discovery of reusable fragments."""

    def __init__(self, fragments_dir: str, logger: Logger):
        """
        Initialize the fragment registry.

        Args:
            fragments_dir: Path to directory containing fragment definitions
            logger: Logger instance
        """
        self._fragments: Dict[str, FragmentSchema] = {}
        super().__init__(fragments_dir, logger)

    def _load_items(self) -> None:
        """Load all fragments from the fragments directory."""
        if not self.registry_dir.exists():
            self.logger.warning(f"Fragments directory not found: {self.registry_dir}")
            return

        # Load each fragment directory
        for fragment_dir in self.registry_dir.iterdir():
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

                fragment_schema = FragmentSchema(**schema_data)
                fragment_id = fragment_schema.fragment_id

                self._fragments[fragment_id] = fragment_schema
                self.logger.info(
                    f"Loaded fragment: {fragment_id} ({fragment_schema.name})"
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to load fragment from {fragment_dir.name}: {e}"
                )

    def list_fragments(self) -> List[FragmentListItem]:
        """Get a list of all available fragments."""
        return [
            FragmentListItem(
                fragment_id=schema.fragment_id,
                name=schema.name,
                description=schema.description,
                parameter_count=len(schema.parameters),
            )
            for schema in self._fragments.values()
        ]

    def get_fragment_schema(self, fragment_id: str) -> Optional[FragmentSchema]:
        """Get the full schema for a fragment."""
        return self._fragments.get(fragment_id)

    def fragment_exists(self, fragment_id: str) -> bool:
        """Check if a fragment exists."""
        return fragment_id in self._fragments

    def get_jinja_template(self, fragment_id: str):
        """Get the Jinja2 template for rendering a fragment."""
        return self._get_jinja_template(f"{fragment_id}/fragment.html.jinja2")

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
```

### 4. Update Fragments Package

**File:** `app/fragments/__init__.py`

```python
"""Fragments package for reusable document content blocks."""
from app.fragments.registry import FragmentRegistry

__all__ = ["FragmentRegistry"]
```

## Benefits

### 1. **Code Reuse**
- BaseRegistry handles common YAML loading, Jinja2 setup, logging
- Both registries implement `_load_items()` with their specific logic

### 2. **Clear Separation**
- TemplateRegistry: Document-scoped (global parameters + embedded fragments)
- FragmentRegistry: Standalone fragments discoverable across templates

### 3. **Parallel APIs**
```python
# Both follow similar patterns
template_registry.get_template_schema(template_id)
fragment_registry.get_fragment_schema(fragment_id)

template_registry.validate_global_parameters(template_id, params)
fragment_registry.validate_parameters(fragment_id, params)

template_registry.get_jinja_template_for_fragment(template_id, fragment_id)
fragment_registry.get_jinja_template(fragment_id)
```

### 4. **Flexible Fragment Use**
- **Embedded**: Fragments defined within `templates/{id}/fragments/` (current TemplateRegistry)
- **Standalone**: Fragments in separate `fragments/{id}/` directory (new FragmentRegistry)
- **Mixed**: Applications can use both patterns

### 5. **Extensibility**
- New registry types (DataSourceRegistry, LayoutRegistry) can extend BaseRegistry
- Common functionality inherited automatically

## Directory Structure

```
templates/
├── basic_report/
│   ├── template.yaml
│   ├── document.html.jinja2
│   └── fragments/
│       ├── paragraph.html.jinja2
│       └── section.html.jinja2

fragments/                    # NEW: Standalone fragments
├── paragraph/
│   ├── fragment.yaml
│   └── fragment.html.jinja2
├── sidebar/
│   ├── fragment.yaml
│   └── fragment.html.jinja2
└── footer/
    ├── fragment.yaml
    └── fragment.html.jinja2
```

## Schema Examples

### Fragment YAML (`fragment.yaml`)

```yaml
fragment_id: paragraph
name: Paragraph
description: A block of text with optional heading
parameters:
  - name: text
    type: string
    description: Paragraph content
    required: true
  - name: heading
    type: string
    description: Optional paragraph heading
    required: false
```

### Fragment HTML Template (`fragment.html.jinja2`)

```html
<div class="fragment-paragraph">
  {% if heading %}
    <h3>{{ heading }}</h3>
  {% endif %}
  <p>{{ text }}</p>
</div>
```

## Integration Points

1. **MCP Server** uses both registries:
   - TemplateRegistry for `list_templates`, `get_template_details`
   - FragmentRegistry (optionally) for global fragment discovery

2. **Session Manager** uses registries:
   - TemplateRegistry to validate and render documents
   - FragmentRegistry to validate standalone fragments

3. **Rendering Engine**:
   - Uses both registry types to resolve templates and fragments
   - Renders document with embedded + standalone fragments

## Next Steps

1. **Create BaseRegistry** and move common logic
2. **Refactor TemplateRegistry** to extend BaseRegistry
3. **Create FragmentRegistry** in fragments/ package
4. **Update validation schemas** to include standalone FragmentSchema
5. **Update rendering engine** to use both registries
6. **Add tests** for fragment discovery and rendering
