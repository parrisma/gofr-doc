"""Table data validation for table fragments.

Validates table structure, parameters, and constraints for the table fragment type.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator, model_validator

from app.exceptions import ValidationError
from app.formatting.number_formatter import validate_format_spec
from app.validation.color_validator import validate_color


class TableValidationError(ValidationError):
    """Table validation errors with structured error information."""

    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(code=error_code, message=message, details=details)
        # Maintain backward compatibility with error_code attribute
        self.error_code = error_code


class TableData(BaseModel):
    """Table data model with validation."""

    rows: List[List[Any]]
    has_header: bool = True
    title: Optional[str] = None
    width: str = "auto"
    column_alignments: Optional[List[str]] = None
    border_style: str = "full"
    zebra_stripe: bool = False
    compact: bool = False
    number_format: Optional[Dict[int, str]] = None
    header_color: Optional[str] = None
    stripe_color: Optional[str] = None
    highlight_rows: Optional[Dict[int, str]] = None
    highlight_columns: Optional[Dict[int, str]] = None
    sort_by: Optional[Any] = None  # str, int, dict, or list of these
    column_widths: Optional[Dict[int, str]] = None  # Column index -> percentage (e.g., "25%")

    @field_validator("rows")
    @classmethod
    def validate_rows(cls, v: List[List[Any]]) -> List[List[Any]]:
        """Validate rows is non-empty array of arrays."""
        if not v:
            raise TableValidationError("INVALID_TABLE_DATA", "Table rows cannot be empty")

        if not isinstance(v, list):
            raise TableValidationError("INVALID_TABLE_DATA", "Table rows must be an array")

        if not all(isinstance(row, list) for row in v):
            raise TableValidationError("INVALID_TABLE_DATA", "Each row must be an array")

        return v

    @model_validator(mode="after")
    def validate_consistent_columns(self) -> "TableData":
        """Validate all rows have the same number of columns."""
        if not self.rows:
            return self

        column_counts = [len(row) for row in self.rows]
        if len(set(column_counts)) > 1:
            raise TableValidationError(
                "INCONSISTENT_COLUMNS",
                f"All rows must have the same number of columns. Found: {column_counts}",
            )

        # Validate column_alignments count matches column count
        if self.column_alignments is not None:
            column_count = self.get_column_count()
            if len(self.column_alignments) != column_count:
                raise TableValidationError(
                    "ALIGNMENT_COUNT_MISMATCH",
                    f"Number of alignments ({len(self.column_alignments)}) must match number of columns ({column_count})",
                )

        # Validate number_format column indices don't exceed column count
        if self.number_format is not None:
            column_count = self.get_column_count()
            for col_index in self.number_format.keys():
                if col_index >= column_count:
                    raise TableValidationError(
                        "INVALID_NUMBER_FORMAT",
                        f"Column index {col_index} exceeds number of columns ({column_count})",
                    )

        # Validate highlight_rows indices don't exceed row count
        if self.highlight_rows is not None:
            row_count = self.get_row_count()
            for row_index in self.highlight_rows.keys():
                if row_index >= row_count:
                    raise TableValidationError(
                        "INVALID_HIGHLIGHT",
                        f"Row index {row_index} exceeds number of rows ({row_count})",
                    )

        # Validate highlight_columns indices don't exceed column count
        if self.highlight_columns is not None:
            column_count = self.get_column_count()
            for col_index in self.highlight_columns.keys():
                if col_index >= column_count:
                    raise TableValidationError(
                        "INVALID_HIGHLIGHT",
                        f"Column index {col_index} exceeds number of columns ({column_count})",
                    )

        # Validate sort_by references valid columns
        if self.sort_by is not None:
            specs = self.sort_by if isinstance(self.sort_by, list) else [self.sort_by]
            column_count = self.get_column_count()
            header_row = self.rows[0] if self.has_header else None

            for spec in specs:
                # Extract column from spec
                if isinstance(spec, str):
                    # Column name - requires header
                    if not self.has_header or not header_row:
                        raise TableValidationError(
                            "INVALID_SORT",
                            "Sorting by column name requires has_header=True",
                        )
                    if spec not in header_row:
                        raise TableValidationError(
                            "INVALID_SORT",
                            f"Sort column '{spec}' not found in header row",
                        )
                elif isinstance(spec, int):
                    # Column index
                    if spec >= column_count:
                        raise TableValidationError(
                            "INVALID_SORT",
                            f"Sort column index {spec} exceeds number of columns ({column_count})",
                        )
                elif isinstance(spec, dict):
                    col = spec["column"]
                    if isinstance(col, str):
                        if not self.has_header or not header_row:
                            raise TableValidationError(
                                "INVALID_SORT",
                                "Sorting by column name requires has_header=True",
                            )
                        if col not in header_row:
                            raise TableValidationError(
                                "INVALID_SORT",
                                f"Sort column '{col}' not found in header row",
                            )
                    elif isinstance(col, int):
                        if col >= column_count:
                            raise TableValidationError(
                                "INVALID_SORT",
                                f"Sort column index {col} exceeds number of columns ({column_count})",
                            )

        # Validate column_widths indices don't exceed column count
        if self.column_widths is not None:
            column_count = self.get_column_count()
            for col_index in self.column_widths.keys():
                if col_index >= column_count:
                    raise TableValidationError(
                        "INVALID_COLUMN_WIDTH",
                        f"Column index {col_index} exceeds number of columns ({column_count})",
                    )

        return self

    @field_validator("width")
    @classmethod
    def validate_width(cls, v: str) -> str:
        """Validate width parameter."""
        if v not in ["auto", "full"] and not v.endswith("%"):
            raise TableValidationError(
                "INVALID_WIDTH",
                f"Width must be 'auto', 'full', or a percentage (e.g., '80%'). Got: {v}",
            )

        if v.endswith("%"):
            try:
                percent = int(v[:-1])
                if percent < 1 or percent > 100:
                    raise ValueError
            except ValueError:
                raise TableValidationError("INVALID_WIDTH", f"Invalid percentage value: {v}")

        return v

    @field_validator("column_alignments")
    @classmethod
    def validate_column_alignments(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate column alignments."""
        if v is None:
            return v

        valid_alignments = ["left", "center", "right"]
        for alignment in v:
            if alignment not in valid_alignments:
                raise TableValidationError(
                    "INVALID_ALIGNMENT",
                    f"Alignment must be one of {valid_alignments}. Got: {alignment}",
                )

        return v

    @field_validator("border_style")
    @classmethod
    def validate_border_style(cls, v: str) -> str:
        """Validate border style."""
        valid_styles = ["full", "horizontal", "minimal", "none"]
        if v not in valid_styles:
            raise TableValidationError(
                "INVALID_BORDER_STYLE",
                f"Border style must be one of {valid_styles}. Got: {v}",
            )

        return v

    @field_validator("number_format")
    @classmethod
    def validate_number_format(cls, v: Optional[Dict[int, str]]) -> Optional[Dict[int, str]]:
        """Validate number format specifications."""
        if v is None:
            return v

        # Validate each format specification
        for col_index, format_spec in v.items():
            # Convert string keys to integers (from JSON serialization)
            if isinstance(col_index, str):
                try:
                    col_index = int(col_index)
                except ValueError:
                    raise TableValidationError(
                        "INVALID_NUMBER_FORMAT",
                        f"Column index must be a non-negative integer. Got: {col_index}",
                    )

            # Validate column index is non-negative
            if not isinstance(col_index, int) or col_index < 0:
                raise TableValidationError(
                    "INVALID_NUMBER_FORMAT",
                    f"Column index must be a non-negative integer. Got: {col_index}",
                )

            # Validate format specification
            if not validate_format_spec(format_spec):
                raise TableValidationError(
                    "INVALID_NUMBER_FORMAT",
                    f"Invalid format specification for column {col_index}: {format_spec}",
                )

        return v

    @field_validator("header_color")
    @classmethod
    def validate_header_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate header color."""
        if v is None:
            return v

        if not validate_color(v):
            raise TableValidationError(
                "INVALID_COLOR",
                f"Invalid header color. Must be theme color (blue, orange, etc.) or hex color. Got: {v}",
            )

        return v

    @field_validator("stripe_color")
    @classmethod
    def validate_stripe_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate stripe color."""
        if v is None:
            return v

        if not validate_color(v):
            raise TableValidationError(
                "INVALID_COLOR",
                f"Invalid stripe color. Must be theme color (blue, orange, etc.) or hex color. Got: {v}",
            )

        return v

    @field_validator("highlight_rows")
    @classmethod
    def validate_highlight_rows(cls, v: Optional[Dict[int, str]]) -> Optional[Dict[int, str]]:
        """Validate highlight rows."""
        if v is None:
            return v

        for row_index, color in v.items():
            # Convert string keys to integers (from JSON serialization)
            if isinstance(row_index, str):
                try:
                    row_index = int(row_index)
                except ValueError:
                    raise TableValidationError(
                        "INVALID_HIGHLIGHT",
                        f"Row index must be a non-negative integer. Got: {row_index}",
                    )

            # Validate row index is non-negative
            if not isinstance(row_index, int) or row_index < 0:
                raise TableValidationError(
                    "INVALID_HIGHLIGHT",
                    f"Row index must be a non-negative integer. Got: {row_index}",
                )

            # Validate color
            if not validate_color(color):
                raise TableValidationError(
                    "INVALID_COLOR",
                    f"Invalid color for row {row_index}. Must be theme color or hex color. Got: {color}",
                )

        return v

    @field_validator("highlight_columns")
    @classmethod
    def validate_highlight_columns(cls, v: Optional[Dict[int, str]]) -> Optional[Dict[int, str]]:
        """Validate highlight columns."""
        if v is None:
            return v

        for col_index, color in v.items():
            # Convert string keys to integers (from JSON serialization)
            if isinstance(col_index, str):
                try:
                    col_index = int(col_index)
                except ValueError:
                    raise TableValidationError(
                        "INVALID_HIGHLIGHT",
                        f"Column index must be a non-negative integer. Got: {col_index}",
                    )

            # Validate column index is non-negative
            if not isinstance(col_index, int) or col_index < 0:
                raise TableValidationError(
                    "INVALID_HIGHLIGHT",
                    f"Column index must be a non-negative integer. Got: {col_index}",
                )

            # Validate color
            if not validate_color(color):
                raise TableValidationError(
                    "INVALID_COLOR",
                    f"Invalid color for column {col_index}. Must be theme color or hex color. Got: {color}",
                )

        return v

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: Optional[Any]) -> Optional[Any]:
        """Validate sort_by parameter."""
        if v is None:
            return v

        # Normalize to list
        specs = v if isinstance(v, list) else [v]

        for spec in specs:
            if isinstance(spec, str):
                # Column name - will be validated against header later
                pass
            elif isinstance(spec, int):
                # Column index - will be validated against column count later
                if spec < 0:
                    raise TableValidationError(
                        "INVALID_SORT",
                        f"Sort column index must be non-negative. Got: {spec}",
                    )
            elif isinstance(spec, dict):
                # Validate dict structure
                if "column" not in spec:
                    raise TableValidationError(
                        "INVALID_SORT",
                        "Sort specification dict must have 'column' key",
                    )

                col = spec["column"]
                if not isinstance(col, (str, int)):
                    raise TableValidationError(
                        "INVALID_SORT",
                        f"Sort column must be string or int. Got: {type(col).__name__}",
                    )

                if isinstance(col, int) and col < 0:
                    raise TableValidationError(
                        "INVALID_SORT",
                        f"Sort column index must be non-negative. Got: {col}",
                    )

                # Validate order if present
                if "order" in spec:
                    order = spec["order"]
                    if order not in ["asc", "desc"]:
                        raise TableValidationError(
                            "INVALID_SORT",
                            f"Sort order must be 'asc' or 'desc'. Got: {order}",
                        )
            else:
                raise TableValidationError(
                    "INVALID_SORT",
                    f"Sort specification must be string, int, or dict. Got: {type(spec).__name__}",
                )

        return v

    @field_validator("column_widths")
    @classmethod
    def validate_column_widths(cls, v: Optional[Dict[int, str]]) -> Optional[Dict[int, str]]:
        """Validate column_widths parameter."""
        if v is None:
            return v

        total_percentage = 0
        for col_index, width_str in v.items():
            # Convert string keys to integers (JSON serialization converts int keys to strings)
            if isinstance(col_index, str):
                try:
                    col_index = int(col_index)
                except ValueError:
                    raise TableValidationError(
                        "INVALID_COLUMN_WIDTH",
                        f"Column index must be a non-negative integer. Got: {col_index}",
                    )

            # Validate column index
            if not isinstance(col_index, int) or col_index < 0:
                raise TableValidationError(
                    "INVALID_COLUMN_WIDTH",
                    f"Column index must be a non-negative integer. Got: {col_index}",
                )

            # Validate percentage format
            if not isinstance(width_str, str) or not width_str.endswith("%"):
                raise TableValidationError(
                    "INVALID_COLUMN_WIDTH",
                    f"Column width must be a percentage string (e.g., '25%'). Got: {width_str}",
                )

            # Extract and validate percentage value
            try:
                percentage = float(width_str[:-1])
            except ValueError:
                raise TableValidationError(
                    "INVALID_COLUMN_WIDTH",
                    f"Invalid percentage format: {width_str}",
                )

            if percentage <= 0 or percentage > 100:
                raise TableValidationError(
                    "INVALID_COLUMN_WIDTH",
                    f"Column width percentage must be between 0 and 100. Got: {percentage}%",
                )

            total_percentage += percentage

        # Validate total doesn't exceed 100%
        if total_percentage > 100:
            raise TableValidationError(
                "INVALID_COLUMN_WIDTH",
                f"Total column widths ({total_percentage}%) exceed 100%",
            )

        return v

    def get_column_count(self) -> int:
        """Get the number of columns in the table."""
        return len(self.rows[0]) if self.rows else 0

    def get_row_count(self) -> int:
        """Get the number of rows in the table."""
        return len(self.rows)

    def get_data_rows(self) -> List[List[Any]]:
        """Get data rows (excluding header if has_header=True)."""
        if self.has_header and len(self.rows) > 1:
            return self.rows[1:]
        return self.rows if not self.has_header else []

    def get_header_row(self) -> Optional[List[Any]]:
        """Get header row if has_header=True."""
        if self.has_header and self.rows:
            return self.rows[0]
        return None


def validate_table_data(data: Dict[str, Any]) -> TableData:
    """Validate table data and return TableData model.

    Args:
        data: Dictionary containing table parameters

    Returns:
        TableData: Validated table data model

    Raises:
        TableValidationError: If validation fails
    """
    try:
        return TableData(**data)
    except TableValidationError:
        raise
    except Exception as e:
        raise TableValidationError("INVALID_TABLE_DATA", f"Invalid table data: {str(e)}")
