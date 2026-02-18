"""Discovery tool handlers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.mcp_server.responses import _error, _model_dump, _success
from app.mcp_server.state import ensure_style_registry, ensure_template_registry
from app.mcp_server.tool_types import ToolResponse
from app.validation.document_models import (
    FragmentDetailsOutput,
    FragmentListItem,
    GetFragmentDetailsInput,
    GetTemplateDetailsInput,
    ListTemplateFragmentsInput,
    PingOutput,
)


async def _tool_ping(arguments: Dict[str, Any]) -> ToolResponse:
    output = PingOutput(
        status="ok",
        timestamp=datetime.utcnow().isoformat(),
        message="Document generation service is online.",
    )
    return _success(_model_dump(output))


async def _tool_list_templates(arguments: Dict[str, Any]) -> ToolResponse:
    registry = ensure_template_registry()
    templates = [
        {
            "template_id": item.template_id,
            "name": item.name,
            "description": item.description,
            "group": item.group,
        }
        for item in registry.list_templates()
    ]
    return _success({"templates": templates})


async def _tool_get_template_details(arguments: Dict[str, Any]) -> ToolResponse:
    payload = GetTemplateDetailsInput.model_validate(arguments)
    registry = ensure_template_registry()
    details = registry.get_template_details(payload.template_id)
    if details is None:
        # Get available templates to help with recovery
        available = [t.template_id for t in registry.list_templates()]
        return _error(
            code="TEMPLATE_NOT_FOUND",
            message=f"Template '{payload.template_id}' does not exist in the registry.",
            recovery=(
                "Call list_templates to discover available templates. "
                f"Available options: {', '.join(available) if available else 'none'}. "
                "Then retry with a valid template_id."
            ),
        )
    return _success(_model_dump(details))


async def _tool_list_template_fragments(arguments: Dict[str, Any]) -> ToolResponse:
    payload = ListTemplateFragmentsInput.model_validate(arguments)
    registry = ensure_template_registry()
    schema = registry.get_template_schema(payload.template_id)
    if schema is None:
        available = [t.template_id for t in registry.list_templates()]
        return _error(
            code="TEMPLATE_NOT_FOUND",
            message=(
                f"Template '{payload.template_id}' does not exist. "
                "Cannot list fragments for non-existent template."
            ),
            recovery=(
                "First call list_templates to discover available templates: "
                f"{', '.join(available) if available else 'none available'}. "
                "Then retry with a valid template_id."
            ),
        )

    fragments = [
        FragmentListItem(
            fragment_id=fragment.fragment_id,
            name=fragment.name,
            description=fragment.description,
            parameter_count=len(fragment.parameters),
        ).model_dump(mode="json")
        for fragment in schema.fragments
    ]
    return _success({"template_id": payload.template_id, "fragments": fragments})


async def _tool_get_fragment_details(arguments: Dict[str, Any]) -> ToolResponse:
    payload = GetFragmentDetailsInput.model_validate(arguments)
    registry = ensure_template_registry()
    fragment_schema = registry.get_fragment_schema(payload.template_id, payload.fragment_id)
    if fragment_schema is None:
        # Get available fragments to help with recovery
        template_schema = registry.get_template_schema(payload.template_id)
        if template_schema:
            available_fragments = [f.fragment_id for f in template_schema.fragments]
            return _error(
                code="FRAGMENT_NOT_FOUND",
                message=(
                    f"Fragment '{payload.fragment_id}' does not exist in template '{payload.template_id}'."
                ),
                recovery=(
                    f"Call list_template_fragments(template_id='{payload.template_id}') "
                    f"to see available fragments: {', '.join(available_fragments)}. "
                    "Then retry with a valid fragment_id."
                ),
            )
        else:
            return _error(
                code="FRAGMENT_NOT_FOUND",
                message=(
                    f"Fragment '{payload.fragment_id}' not found. "
                    f"Template '{payload.template_id}' may not exist."
                ),
                recovery=(
                    "First verify the template exists by calling list_templates, "
                    "then call list_template_fragments to see available fragments."
                ),
            )

    details = FragmentDetailsOutput(
        template_id=payload.template_id,
        fragment_id=fragment_schema.fragment_id,
        name=fragment_schema.name,
        description=fragment_schema.description,
        parameters=fragment_schema.parameters,
    )
    return _success(_model_dump(details))


async def _tool_list_styles(arguments: Dict[str, Any]) -> ToolResponse:
    registry = ensure_style_registry()
    styles = [
        {
            "style_id": item.style_id,
            "name": item.name,
            "description": item.description,
        }
        for item in registry.list_styles()
    ]
    return _success({"styles": styles})


async def _tool_help(arguments: Dict[str, Any]) -> ToolResponse:
    """Provide comprehensive workflow documentation and guidance."""
    from app.validation.document_models import HelpOutput

    output = HelpOutput(
        service_name="gofr-doc-document-service",
        version="1.21.0",
        workflow_overview=(
            "WORKFLOW: DISCOVERY -> SESSION -> CONFIG -> BUILD -> RENDER\n"
            "1. DISCOVERY: list_templates, get_template_details, list_template_fragments\n"
            "2. SESSION: create_document_session\n"
            "3. CONFIG: set_global_parameters (title, author, etc.)\n"
            "4. BUILD: add_fragment repeatedly\n"
            "5. RENDER: get_document (HTML/PDF/Markdown)\n\n"
            "SECURITY: JWT Bearer token required for sessions. Group-isolated: you only see YOUR sessions.\n"
            "Discovery tools (list_templates, get_template_details, list_styles) do NOT need auth."
        ),
        guid_persistence=(
            "CRITICAL: UUID HANDLING (36-char format only)\n"
            "Format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx | Example: 61ea2281-c8df-4719-b71e-56a1305352cc\n"
            "[Y] Copy/paste EXACT | [N] Never retype (b71e != b77e) | [N] Never truncate | Case-sensitive\n\n"
            "THREE GUID TYPES:\n"
            "1. session_id: Document config (reusable, save immediately after create_document_session)\n"
            "2. fragment_instance_guid: Unique per add_fragment call (use to remove specific fragments)\n"
            "3. proxy_guid: One specific rendered output (DIFFERENT from session_id!)\n\n"
            "PROXY MODE (session_id != proxy_guid):\n"
            "session_id = recipe (reusable) | proxy_guid = baked cake (one specific render)\n"
            "One session -> many proxy_guids (different formats/styles)\n"
            "Download: GET /proxy/{proxy_guid} with Authorization header (NOT /proxy/{session_id}!)"
        ),
        common_pitfalls=[
            "Not saving session_id immediately after create_document_session",
            "Retyping/modifying UUIDs (b71e != b77e) or truncating them (61ea2281-... invalid)",
            "Global parameters AFTER fragments (must be BEFORE) | AVOID:  Wrong parameter names",
            "Confusing session_id (config/reusable) with proxy_guid (rendered/one-time)",
            "Downloading proxy via /proxy/{session_id} instead of /proxy/{proxy_guid}",
            "Missing Authorization header on proxy downloads",
            "TABLE: Widths total >100% | 1-based indices (use 0-based) | Capitalized colors",
            "TABLE: Missing # in hex | Wrong format ('USD' not 'currency:USD') | sort_by column name when no header",
            "IMAGE: Not testing URL in browser first | Behind login | Missing image/* Content-Type",
            "IMAGE: HTTP without require_https=false | Both width AND height (distorts) | >10MB",
        ],
        example_workflows=[
            {
                "name": "QUICK START: Create & Render Document",
                "steps": [
                    "1. list_templates() -> Pick a template_id",
                    "2. create_document_session(template_id='...') -> Save session_id",
                    "3. set_global_parameters(session_id='...', parameters={title: '...', author: '...'})",
                    "4. add_fragment(session_id='...', fragment_id='heading', parameters={text: '...'})",
                    "5. add_fragment(session_id='...', fragment_id='paragraph', parameters={text: '...'})",
                    "6. get_document(session_id='...', format='html') -> Get HTML directly",
                    "",
                    "ALTERNATIVE (for large docs):",
                    "6. get_document(session_id='...', format='pdf', proxy=true) -> Save proxy_guid",
                    "7. GET /proxy/{proxy_guid} with Authorization header -> Download PDF from web",
                ],
            },
            {
                "name": "Validate Before Adding",
                "steps": [
                    "validate_parameters(template_id='...', parameter_type='global', parameters={...})",
                    "validate_parameters(template_id='...', parameter_type='fragment', fragment_id='...', parameters={...})",
                    "Only call add_fragment/set_global_parameters if is_valid=true",
                ],
            },
            {
                "name": "Table with Formatting",
                "steps": [
                    "create_document_session -> set_global_parameters -> add_fragment with:",
                    "  rows: [[...]], has_header: true, column_widths: {0: '40%', 1: '30%', 2: '30%'},",
                    "  column_alignments: ['left','right','right'],",
                    "  number_format: {1: 'currency:USD', 2: 'decimal:2'},",
                    "  header_color: 'primary', zebra_stripe: true",
                ],
            },
            {
                "name": "Add Images",
                "steps": [
                    "1. Test image URL in browser first (must show Content-Type: image/*)",
                    "2. add_image_fragment(session_id='...', image_url='https://...', width=600, alignment='center')",
                    "3. If error, check error_code: INVALID_IMAGE_URL (use HTTPS), IMAGE_URL_NOT_ACCESSIBLE (check if public)",
                    "4. INVALID_IMAGE_CONTENT_TYPE (wrong format), IMAGE_TOO_LARGE (compress)",
                ],
            },
        ],
        tool_sequence=[
            {
                "category": "DISCOVERY",
                "tools": [
                    "ping",
                    "list_templates",
                    "get_template_details",
                    "list_template_fragments",
                    "get_fragment_details",
                    "list_styles",
                ],
            },
            {
                "category": "SESSION",
                "tools": [
                    "create_document_session",
                    "list_active_sessions",
                    "get_session_status",
                    "abort_document_session",
                ],
            },
            {"category": "VALIDATION", "tools": ["validate_parameters"]},
            {
                "category": "BUILD",
                "tools": [
                    "set_global_parameters",
                    "add_fragment",
                    "add_image_fragment",
                    "remove_fragment",
                    "list_session_fragments",
                ],
            },
            {"category": "RENDER", "tools": ["get_document"]},
        ],
        authoring_guide=[
            "All content lives under data/{templates,fragments,styles}/<group>/. The <group> directory name controls access isolation (e.g. public, team1).",
            "TEMPLATE: Directory is data/templates/<group>/<template_id>/. Required files: template.yaml (schema: metadata + global_parameters + fragments list), document.html.jinja2 (outer HTML wrapper receiving {{ title }}, {{ css }}, {{ fragments }}), and a fragments/ subdirectory with one .html.jinja2 per fragment declared in the YAML.",
            "template.yaml skeleton: metadata: {template_id: my_report, group: public, name: My Report, description: A custom report template}. global_parameters: [{name: title, type: string, required: true}, {name: author, type: string, required: false}]. fragments: [{fragment_id: paragraph, name: Paragraph, parameters: [{name: text, type: string, required: true}]}]",
            "document.html.jinja2 minimal example: <html><head><style>{{ css }}</style></head><body><h1>{{ title }}</h1>{% for f in fragments %}{{ f.html|safe }}{% endfor %}</body></html>",
            "Fragment Jinja2 example (fragments/paragraph.html.jinja2): <div class='fragment-paragraph'><p>{{ text }}</p></div>",
            "STANDALONE FRAGMENT: Directory is data/fragments/<group>/<fragment_id>/. Required files: fragment.yaml (schema: fragment_id, group, name, description, parameters) and fragment.html.jinja2 (Jinja2 template receiving declared parameters as variables).",
            "fragment.yaml skeleton: {fragment_id: callout, group: public, name: Callout Box, description: A highlighted callout, parameters: [{name: text, type: string, required: true}, {name: style, type: string, required: false, default: info}]}",
            "STYLE: Directory is data/styles/<group>/<style_id>/. Required files: style.yaml (metadata: style_id, group, name, description) and style.css (CSS injected into documents via {{ css }}).",
            "RULE: template_id / fragment_id / style_id MUST match their directory name.",
            "RULE: group field in YAML MUST match the parent group directory name.",
            "RULE: Parameter types are string, integer, number, boolean, array, object.",
            "RULE: Restart the service after adding new content (registries scan at startup).",
        ],
    )

    return _success(_model_dump(output))
