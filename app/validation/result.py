"""Validation result model for document generation system."""
from typing import Any, Dict, List
from pydantic import BaseModel
from app.validation.error import ValidationError


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
