"""Validation error model for document generation system."""

from typing import Any, List
from pydantic import BaseModel, ConfigDict


class ValidationError(BaseModel):
    """Detailed validation error with helpful suggestions"""

    field: str
    message: str
    received_value: Any = None
    expected: str
    suggestions: List[str] = []

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "template_id",
                "message": "Template not found",
                "received_value": "unknown_template",
                "expected": "Valid template identifier",
                "suggestions": ["Call list_templates to see available templates"],
            }
        }
    )
