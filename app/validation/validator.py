"""Validator for document generation system matching mcp_server interface."""
from typing import Any, Dict, List, Optional
from app.validation.models import ValidationError, ValidationResult


class Validator:
    """Validates document operations with helpful error messages."""

    def __init__(self):
        """Initialize validator with valid values."""
        self.valid_formats = ["html", "pdf", "md"]
        self.valid_positions = ["start", "end"]

    def validate(self, data: Any) -> ValidationResult:
        """
        Validate arbitrary data and return structured validation results.

        Args:
            data: The data to validate

        Returns:
            ValidationResult with errors
        """
        try:
            # If no data, that's valid
            if data is None:
                return ValidationResult(is_valid=True, errors=[])

            # If it's a dict, try basic validation
            if isinstance(data, dict):
                return self._validate_dict(data)

            # For other types, assume valid
            return ValidationResult(is_valid=True, errors=[])

        except Exception as e:
            # Ultimate fallback
            return ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(
                        field="validation_system",
                        message=f"Critical validation error: {str(e)}",
                        received_value=None,
                        expected="Valid input",
                        suggestions=[
                            "The validation system encountered an unexpected error",
                            "Please check your input data format",
                        ],
                    )
                ],
            )

    def validate_document_session(self, session_id: str) -> ValidationResult:
        """Validate document session identifier."""
        errors: List[ValidationError] = []

        if not session_id or not isinstance(session_id, str):
            errors.append(
                ValidationError(
                    field="session_id",
                    message="Session ID must be a non-empty string",
                    received_value=session_id,
                    expected="Non-empty string",
                    suggestions=[
                        "Create a new session using create_document_session",
                        "Verify the session ID is valid and exists",
                    ],
                )
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def validate_template_id(self, template_id: str) -> ValidationResult:
        """Validate template identifier."""
        errors: List[ValidationError] = []

        if not template_id or not isinstance(template_id, str):
            errors.append(
                ValidationError(
                    field="template_id",
                    message="Template ID must be a non-empty string",
                    received_value=template_id,
                    expected="Non-empty string",
                    suggestions=[
                        "Call list_templates to see available templates",
                        "Provide a valid template identifier",
                    ],
                )
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def validate_fragment_id(self, fragment_id: str) -> ValidationResult:
        """Validate fragment identifier."""
        errors: List[ValidationError] = []

        if not fragment_id or not isinstance(fragment_id, str):
            errors.append(
                ValidationError(
                    field="fragment_id",
                    message="Fragment ID must be a non-empty string",
                    received_value=fragment_id,
                    expected="Non-empty string",
                    suggestions=[
                        "Call list_template_fragments to see available fragments",
                        "Provide a valid fragment identifier",
                    ],
                )
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def validate_output_format(self, format_str: str) -> ValidationResult:
        """Validate output format."""
        errors: List[ValidationError] = []

        if format_str not in self.valid_formats:
            errors.append(
                ValidationError(
                    field="format",
                    message=f"Invalid output format '{format_str}'",
                    received_value=format_str,
                    expected=f"One of: {', '.join(self.valid_formats)}",
                    suggestions=[
                        "Use 'html' for HTML output",
                        "Use 'pdf' for PDF documents",
                        "Use 'md' for Markdown output",
                    ],
                )
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def validate_parameters(self, parameters: Dict[str, Any]) -> ValidationResult:
        """Validate document parameters."""
        errors: List[ValidationError] = []

        if not isinstance(parameters, dict):
            errors.append(
                ValidationError(
                    field="parameters",
                    message="Parameters must be a dictionary",
                    received_value=type(parameters).__name__,
                    expected="Dictionary (object)",
                    suggestions=[
                        "Provide parameters as a JSON object",
                        "Example: {'param1': 'value1', 'param2': 'value2'}",
                    ],
                )
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def validate_fragment_position(self, position: Optional[str]) -> ValidationResult:
        """Validate fragment insertion position."""
        errors: List[ValidationError] = []

        if position is None:
            # None defaults to "end", which is valid
            return ValidationResult(is_valid=True, errors=[])

        valid_starts = ["start", "end", "before:", "after:"]
        is_valid = any(position.startswith(prefix) for prefix in valid_starts)

        if not is_valid:
            errors.append(
                ValidationError(
                    field="position",
                    message=f"Invalid position '{position}'",
                    received_value=position,
                    expected="start, end, before:<guid>, or after:<guid>",
                    suggestions=[
                        "Use 'start' to insert at the beginning",
                        "Use 'end' to insert at the end (default)",
                        "Use 'before:<guid>' to insert before a fragment",
                        "Use 'after:<guid>' to insert after a fragment",
                    ],
                )
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def _validate_dict(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate a dictionary structure."""
        errors: List[ValidationError] = []

        # Basic checks - could be extended based on requirements
        if not isinstance(data, dict):
            errors.append(
                ValidationError(
                    field="root",
                    message="Expected a dictionary",
                    received_value=type(data).__name__,
                    expected="Dictionary (object)",
                    suggestions=["Provide valid JSON object"],
                )
            )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

