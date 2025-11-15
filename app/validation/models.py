"""Validation models for document generation system."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ValidationError(BaseModel):
    """Detailed validation error with helpful suggestions"""

    field: str
    message: str
    received_value: Any = None
    expected: str
    suggestions: List[str] = []

    class Config:
        json_schema_extra = {
            "example": {
                "field": "template_id",
                "message": "Template not found",
                "received_value": "unknown_template",
                "expected": "Valid template identifier",
                "suggestions": ["Call list_templates to see available templates"]
            }
        }


class ValidationResult(BaseModel):
    """Result of validation with errors and suggestions"""

    is_valid: bool
    errors: List[ValidationError] = []

    def get_error_summary(self) -> str:
        """Get a formatted summary of all errors"""
        if not self.errors:
            return "No errors"

        lines = ["Validation failed with the following errors:\n"]
        for i, error in enumerate(self.errors, 1):
            lines.append(f"{i}. {error.field}: {error.message}")
            lines.append(f"   Received: {error.received_value}")
            lines.append(f"   Expected: {error.expected}")
            if error.suggestions:
                lines.append("   Suggestions:")
                for suggestion in error.suggestions:
                    lines.append(f"   - {suggestion}")
            lines.append("")

        return "\n".join(lines)

    def get_json_errors(self) -> List[Dict[str, Any]]:
        """Get errors in JSON-friendly format"""
        return [
            {
                "field": err.field,
                "message": err.message,
                "received": err.received_value,
                "expected": err.expected,
                "suggestions": err.suggestions,
            }
            for err in self.errors
        ]
