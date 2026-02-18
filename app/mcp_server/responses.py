"""MCP server response helpers.

This module holds low-level helpers used by MCP tool handlers and routing:
- JSON serialization helpers
- success/error response formatting
- Pydantic validation error formatting

Behavior must remain identical to the legacy helpers previously defined in
app/mcp_server/mcp_server.py.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

from mcp.types import EmbeddedResource, ImageContent, TextContent
from pydantic import ValidationError as PydanticValidationError

from app.validation.document_models import ErrorResponse

ToolResponse = List[Union[TextContent, ImageContent, EmbeddedResource]]


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for non-standard types."""
    # Handle Pydantic models
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    # Handle dataclasses and regular objects
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    # Fallback
    return str(obj)


def _json_text(payload: Dict[str, Any]) -> TextContent:
    return TextContent(
        type="text",
        text=json.dumps(payload, indent=2, ensure_ascii=True, default=_json_serializer),
    )


def _success(data: Any, message: Optional[str] = None) -> ToolResponse:
    payload: Dict[str, Any] = {"status": "success", "data": data}
    if message:
        payload["message"] = message
    return [_json_text(payload)]


def _error(
    code: str, message: str, recovery: str, details: Optional[Dict[str, Any]] = None
) -> ToolResponse:
    error_model = ErrorResponse(
        error_code=code,
        message=message,
        recovery_strategy=recovery,
        details=details,
    )
    payload = {"status": "error", **error_model.model_dump(mode="json")}
    return [_json_text(payload)]


def _handle_validation_error(exc: PydanticValidationError) -> ToolResponse:
    errors = exc.errors()
    details = {"validation_errors": errors}

    # Build helpful recovery message based on error types
    missing_fields = [e["loc"][0] for e in errors if e["type"] == "missing"]
    invalid_types = [e["loc"][0] for e in errors if "type" in e["type"]]

    recovery_msg = "Input validation failed. "
    if missing_fields:
        recovery_msg += f"MISSING REQUIRED FIELDS: {', '.join(str(f) for f in missing_fields)}. "
    if invalid_types:
        recovery_msg += f"INCORRECT TYPES: {', '.join(str(f) for f in invalid_types)}. "
    recovery_msg += "Check the tool's inputSchema for required parameters and their types. Review the 'details' field below for specific errors, correct your input, and retry."

    return _error(
        code="INVALID_ARGUMENTS",
        message=f"Input payload failed validation. {len(errors)} error(s) found.",
        recovery=recovery_msg,
        details=details,
    )


def _model_dump(model: Any) -> Dict[str, Any]:
    """Convert model to dictionary, supporting Pydantic models and dataclasses."""
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    # Handle regular dataclasses and objects with __dict__
    if hasattr(model, "__dict__"):
        result: Dict[str, Any] = {}
        for key, value in model.__dict__.items():
            if hasattr(value, "model_dump"):
                # Nested Pydantic model
                result[key] = value.model_dump(mode="json")
            elif isinstance(value, list):
                # List might contain Pydantic models or regular objects
                converted_list = []
                for item in value:
                    if hasattr(item, "model_dump"):
                        converted_list.append(item.model_dump(mode="json"))
                    elif hasattr(item, "__dict__") and not isinstance(
                        item, (str, int, float, bool, type(None))
                    ):
                        converted_list.append(_model_dump(item))
                    else:
                        converted_list.append(item)
                result[key] = converted_list
            elif hasattr(value, "__dict__") and not isinstance(
                value, (str, int, float, bool, type(None))
            ):
                # Nested regular object - recursively convert it
                result[key] = _model_dump(value)
            else:
                result[key] = value
        return result
    raise TypeError(f"Cannot convert {type(model).__name__} to dictionary")
