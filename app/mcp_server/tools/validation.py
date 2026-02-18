"""Validation tool handlers."""

from __future__ import annotations

from typing import Any, Dict

from app.mcp_server.responses import _error, _model_dump, _success
from app.mcp_server.state import ensure_manager, ensure_template_registry
from app.mcp_server.tool_types import ToolResponse


async def _tool_validate_parameters(arguments: Dict[str, Any]) -> ToolResponse:
    """Validate parameters without saving them."""
    from app.validation.document_models import ValidateParametersInput

    payload = ValidateParametersInput.model_validate(arguments)
    manager = ensure_manager()
    registry = ensure_template_registry()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # SECURITY: Verify template exists in caller's group
    template_schema = registry.get_template_schema(payload.template_id)
    if template_schema is None or template_schema.metadata.group != caller_group:
        return _error(
            code="TEMPLATE_NOT_FOUND",
            message=f"Template '{payload.template_id}' not found in your group",
            recovery="Call list_templates to see templates available in your group.",
        )

    try:
        output = await manager.validate_parameters(
            template_id=payload.template_id,
            parameters=payload.parameters,
            parameter_type=payload.parameter_type,
            fragment_id=payload.fragment_id,
        )
        return _success(_model_dump(output))
    except ValueError as exc:
        return _error(
            code="VALIDATION_ERROR",
            message=str(exc),
            recovery=(
                "Verify the template_id exists (call list_templates) and that fragment_id "
                "is valid (call list_template_fragments)."
            ),
        )
