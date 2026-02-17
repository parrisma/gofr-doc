"""Graph data validator.

Validates GraphParams with helpful error messages and suggestions.
Stripped of gofr-plot's Sanitizer dependency -- validation only.
"""

from typing import List

from app.plot.graph_params import GraphParams
from app.plot.themes import list_themes


class ValidationError:
    """Structured validation error with suggestions."""

    def __init__(
        self,
        field: str,
        message: str,
        received_value=None,
        expected: str = "",
        suggestions: list[str] | None = None,
    ):
        self.field = field
        self.message = message
        self.received_value = received_value
        self.expected = expected
        self.suggestions = suggestions or []

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "message": self.message,
            "received_value": str(self.received_value) if self.received_value is not None else None,
            "expected": self.expected,
            "suggestions": self.suggestions,
        }


class ValidationResult:
    """Result of graph data validation."""

    def __init__(self, is_valid: bool, errors: List[ValidationError] | None = None):
        self.is_valid = is_valid
        self.errors = errors or []


class GraphDataValidator:
    """Validates GraphParams with helpful error messages and suggestions."""

    def __init__(self):
        self.valid_types = ["line", "scatter", "bar"]
        self.valid_formats = ["png", "jpg", "svg", "pdf"]
        self.valid_themes = list_themes()

    def validate(self, data: GraphParams) -> ValidationResult:
        """Validate graph data and return structured validation results."""
        errors: List[ValidationError] = []

        errors.extend(self._validate_arrays(data))
        errors.extend(self._validate_type(data))
        errors.extend(self._validate_format(data))
        errors.extend(self._validate_theme(data))
        errors.extend(self._validate_numeric_ranges(data))
        errors.extend(self._validate_colors(data))

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def _validate_arrays(self, data: GraphParams) -> List[ValidationError]:
        errors = []
        datasets = data.get_datasets()

        if not datasets:
            errors.append(
                ValidationError(
                    field="y1",
                    message="At least one dataset (y1) is required",
                    expected="Non-empty list of numbers in y1",
                    suggestions=[
                        "Provide at least one data point in y1",
                        "Example: y1=[10, 20, 15, 30, 25]",
                    ],
                )
            )
            return errors

        first_len = len(datasets[0][0])

        for i, (y_data, _, _) in enumerate(datasets, 1):
            if not y_data:
                errors.append(
                    ValidationError(
                        field=f"y{i}",
                        message=f"Dataset y{i} cannot be empty",
                        received_value=y_data,
                        expected="Non-empty list of numbers",
                    )
                )

        for i, (y_data, _, _) in enumerate(datasets, 1):
            if y_data and len(y_data) != first_len:
                errors.append(
                    ValidationError(
                        field=f"y{i}",
                        message=(
                            f"All datasets must have the same length. "
                            f"y1 has {first_len} points, y{i} has {len(y_data)} points"
                        ),
                        expected="Arrays of equal length",
                    )
                )

        if data.x is not None and len(data.x) != first_len:
            errors.append(
                ValidationError(
                    field="x",
                    message=(
                        f"X array must match dataset length. "
                        f"X has {len(data.x)} points, datasets have {first_len} points"
                    ),
                    expected="Arrays of equal length",
                    suggestions=["Omit x to use auto-generated indices [0, 1, 2, ...]"],
                )
            )

        if first_len < 2 and data.type == "line":
            errors.append(
                ValidationError(
                    field="y1",
                    message="Line charts require at least 2 data points",
                    received_value=first_len,
                    expected="At least 2 points",
                    suggestions=["Use 'scatter' type for single points"],
                )
            )

        return errors

    def _validate_type(self, data: GraphParams) -> List[ValidationError]:
        errors = []
        if data.type not in self.valid_types:
            errors.append(
                ValidationError(
                    field="type",
                    message=f"Invalid chart type '{data.type}'",
                    received_value=data.type,
                    expected=f"One of: {', '.join(self.valid_types)}",
                    suggestions=[
                        "Use 'line' for line charts",
                        "Use 'scatter' for scatter plots",
                        "Use 'bar' for bar charts",
                    ],
                )
            )
        return errors

    def _validate_format(self, data: GraphParams) -> List[ValidationError]:
        errors = []
        if data.format not in self.valid_formats:
            errors.append(
                ValidationError(
                    field="format",
                    message=f"Invalid output format '{data.format}'",
                    received_value=data.format,
                    expected=f"One of: {', '.join(self.valid_formats)}",
                    suggestions=[
                        "Use 'png' for standard raster images",
                        "Use 'svg' for scalable vector graphics",
                        "Use 'pdf' for documents",
                        "Use 'jpg' for compressed images",
                    ],
                )
            )
        return errors

    def _validate_theme(self, data: GraphParams) -> List[ValidationError]:
        errors = []
        if data.theme not in self.valid_themes:
            errors.append(
                ValidationError(
                    field="theme",
                    message=f"Invalid theme '{data.theme}'",
                    received_value=data.theme,
                    expected=f"One of: {', '.join(self.valid_themes)}",
                    suggestions=[
                        "Use 'light' for bright backgrounds",
                        "Use 'dark' for dark mode",
                        f"Available themes: {', '.join(self.valid_themes)}",
                    ],
                )
            )
        return errors

    def _validate_numeric_ranges(self, data: GraphParams) -> List[ValidationError]:
        errors = []
        if not 0.0 <= data.alpha <= 1.0:
            errors.append(
                ValidationError(
                    field="alpha",
                    message="Alpha (transparency) must be between 0.0 and 1.0",
                    received_value=data.alpha,
                    expected="Number between 0.0 and 1.0",
                )
            )
        if data.line_width <= 0:
            errors.append(
                ValidationError(
                    field="line_width",
                    message="Line width must be positive",
                    received_value=data.line_width,
                    expected="Positive number (typically 0.5 to 5.0)",
                )
            )
        if data.marker_size <= 0:
            errors.append(
                ValidationError(
                    field="marker_size",
                    message="Marker size must be positive",
                    received_value=data.marker_size,
                    expected="Positive number (typically 10 to 200)",
                )
            )
        return errors

    def _validate_colors(self, data: GraphParams) -> List[ValidationError]:
        """Basic color format validation for all color parameters."""
        errors = []
        named_colors = {
            "red", "blue", "green", "yellow", "orange", "purple", "pink",
            "black", "white", "gray", "brown", "cyan", "magenta",
        }

        for i in range(1, 6):
            color = getattr(data, f"color{i}", None)
            if color is None:
                continue
            color_lower = color.lower().strip()
            # Accept named colors, hex (#RRGGBB or #RGB), and rgb(r,g,b)
            if color_lower in named_colors:
                continue
            if color_lower.startswith("#") and len(color_lower) in (4, 7):
                continue
            if color_lower.startswith("rgb(") and color_lower.endswith(")"):
                continue
            errors.append(
                ValidationError(
                    field=f"color{i}",
                    message=f"Invalid color format '{color}'",
                    received_value=color,
                    expected="Named color, hex (#RRGGBB), or rgb(r,g,b)",
                    suggestions=[
                        "Use hex (#FF5733), rgb(255,87,51), or color name (red, blue, etc.)"
                    ],
                )
            )
        return errors
