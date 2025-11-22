"""Tests for table data validation."""

import pytest

from app.validation.table_validator import (
    TableData,
    TableValidationError,
    validate_table_data,
)


class TestTableDataValidation:
    """Tests for basic table data validation."""

    def test_valid_table_data(self):
        """Test valid table data."""
        data = {
            "rows": [
                ["Name", "Age", "City"],
                ["Alice", "30", "NYC"],
                ["Bob", "25", "LA"],
            ]
        }
        table = validate_table_data(data)
        assert table.get_column_count() == 3
        assert table.get_row_count() == 3
        assert table.has_header is True

    def test_empty_rows_error(self):
        """Test that empty rows raise error."""
        data = {"rows": []}
        with pytest.raises(TableValidationError) as exc_info:
            validate_table_data(data)
        assert exc_info.value.error_code == "INVALID_TABLE_DATA"
        assert "empty" in exc_info.value.message.lower()

    def test_rows_not_array(self):
        """Test that non-array rows raise error."""
        data = {"rows": "not an array"}
        with pytest.raises(TableValidationError) as exc_info:
            validate_table_data(data)
        assert exc_info.value.error_code == "INVALID_TABLE_DATA"

    def test_row_not_array(self):
        """Test that non-array row elements raise error."""
        data = {"rows": [["valid"], "not an array"]}
        with pytest.raises(TableValidationError) as exc_info:
            validate_table_data(data)
        assert exc_info.value.error_code == "INVALID_TABLE_DATA"

    def test_inconsistent_columns_error(self):
        """Test that inconsistent column counts raise error."""
        data = {"rows": [["A", "B", "C"], ["1", "2"], ["X", "Y", "Z"]]}
        with pytest.raises(TableValidationError) as exc_info:
            validate_table_data(data)
        assert exc_info.value.error_code == "INCONSISTENT_COLUMNS"
        assert "[3, 2, 3]" in exc_info.value.message

    def test_table_without_header(self):
        """Test table with has_header=False."""
        data = {
            "rows": [["Alice", "30"], ["Bob", "25"]],
            "has_header": False,
        }
        table = validate_table_data(data)
        assert table.has_header is False
        assert table.get_header_row() is None
        assert len(table.get_data_rows()) == 2

    def test_table_with_header(self):
        """Test table with has_header=True."""
        data = {
            "rows": [["Name", "Age"], ["Alice", "30"], ["Bob", "25"]],
            "has_header": True,
        }
        table = validate_table_data(data)
        assert table.has_header is True
        assert table.get_header_row() == ["Name", "Age"]
        assert len(table.get_data_rows()) == 2

    def test_table_with_title(self):
        """Test table with optional title."""
        data = {
            "rows": [["Name", "Age"], ["Alice", "30"]],
            "title": "Employee Roster",
        }
        table = validate_table_data(data)
        assert table.title == "Employee Roster"

    def test_width_auto(self):
        """Test width='auto' (default)."""
        data = {"rows": [["A"]], "width": "auto"}
        table = validate_table_data(data)
        assert table.width == "auto"

    def test_width_full(self):
        """Test width='full'."""
        data = {"rows": [["A"]], "width": "full"}
        table = validate_table_data(data)
        assert table.width == "full"

    def test_width_percentage(self):
        """Test width as percentage."""
        data = {"rows": [["A"]], "width": "80%"}
        table = validate_table_data(data)
        assert table.width == "80%"

    def test_invalid_width(self):
        """Test invalid width value."""
        data = {"rows": [["A"]], "width": "invalid"}
        with pytest.raises(TableValidationError) as exc_info:
            validate_table_data(data)
        assert exc_info.value.error_code == "INVALID_WIDTH"

    def test_invalid_percentage_width(self):
        """Test invalid percentage width."""
        data = {"rows": [["A"]], "width": "150%"}
        with pytest.raises(TableValidationError) as exc_info:
            validate_table_data(data)
        assert exc_info.value.error_code == "INVALID_WIDTH"

    def test_get_column_count(self):
        """Test get_column_count method."""
        data = {"rows": [["A", "B", "C"], ["1", "2", "3"]]}
        table = validate_table_data(data)
        assert table.get_column_count() == 3

    def test_get_row_count(self):
        """Test get_row_count method."""
        data = {"rows": [["A"], ["1"], ["2"], ["3"]]}
        table = validate_table_data(data)
        assert table.get_row_count() == 4

    def test_single_row_table(self):
        """Test table with only one row."""
        data = {"rows": [["Header1", "Header2", "Header3"]], "has_header": True}
        table = validate_table_data(data)
        assert table.get_header_row() == ["Header1", "Header2", "Header3"]
        assert len(table.get_data_rows()) == 0

    def test_mixed_data_types(self):
        """Test table with mixed data types in cells."""
        data = {
            "rows": [
                ["Name", "Age", "Score"],
                ["Alice", 30, 95.5],
                ["Bob", 25, 87],
                ["Charlie", None, "N/A"],
            ]
        }
        table = validate_table_data(data)
        assert table.get_column_count() == 3
        assert table.rows[1][1] == 30  # Integer
        assert table.rows[1][2] == 95.5  # Float
        assert table.rows[3][1] is None  # None
        assert table.rows[3][2] == "N/A"  # String


class TestColumnAlignments:
    """Tests for column alignment validation."""

    def test_valid_alignments(self):
        """Test valid column alignments."""
        data = TableData(
            rows=[["A", "B", "C"], ["1", "2", "3"]], column_alignments=["left", "center", "right"]
        )

        assert data.column_alignments == ["left", "center", "right"]

    def test_invalid_alignment_value(self):
        """Test invalid alignment value."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A", "B"], ["1", "2"]], column_alignments=["left", "middle"])

        assert exc.value.error_code == "INVALID_ALIGNMENT"

    def test_alignment_count_mismatch(self):
        """Test alignment count doesn't match column count."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A", "B", "C"], ["1", "2", "3"]], column_alignments=["left", "center"])

        assert exc.value.error_code == "ALIGNMENT_COUNT_MISMATCH"

    def test_alignment_none_is_valid(self):
        """Test None alignments is valid (uses defaults)."""
        data = TableData(rows=[["A", "B"], ["1", "2"]], column_alignments=None)

        assert data.column_alignments is None

    def test_all_left_alignment(self):
        """Test all columns left aligned."""
        data = TableData(
            rows=[["A", "B", "C"], ["1", "2", "3"]], column_alignments=["left", "left", "left"]
        )

        assert data.column_alignments == ["left", "left", "left"]

    def test_all_center_alignment(self):
        """Test all columns center aligned."""
        data = TableData(rows=[["A", "B"], ["1", "2"]], column_alignments=["center", "center"])

        assert data.column_alignments == ["center", "center"]

    def test_all_right_alignment(self):
        """Test all columns right aligned."""
        data = TableData(rows=[["A", "B"], ["1", "2"]], column_alignments=["right", "right"])

        assert data.column_alignments == ["right", "right"]


class TestBorderStyle:
    """Tests for border style validation."""

    def test_border_full(self):
        """Test full border style."""
        data = TableData(rows=[["A"], ["1"]], border_style="full")

        assert data.border_style == "full"

    def test_border_horizontal(self):
        """Test horizontal border style."""
        data = TableData(rows=[["A"], ["1"]], border_style="horizontal")

        assert data.border_style == "horizontal"

    def test_border_minimal(self):
        """Test minimal border style."""
        data = TableData(rows=[["A"], ["1"]], border_style="minimal")

        assert data.border_style == "minimal"

    def test_border_none(self):
        """Test no border style."""
        data = TableData(rows=[["A"], ["1"]], border_style="none")

        assert data.border_style == "none"

    def test_invalid_border_style(self):
        """Test invalid border style."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A"], ["1"]], border_style="dotted")

        assert exc.value.error_code == "INVALID_BORDER_STYLE"

    def test_default_border_style(self):
        """Test default border style is 'full'."""
        data = TableData(rows=[["A"], ["1"]])

        assert data.border_style == "full"


class TestZebraStripe:
    """Tests for zebra striping validation."""

    def test_zebra_stripe_true(self):
        """Test zebra stripe enabled."""
        data = TableData(rows=[["A"], ["1"], ["2"]], zebra_stripe=True)

        assert data.zebra_stripe is True

    def test_zebra_stripe_false(self):
        """Test zebra stripe disabled."""
        data = TableData(rows=[["A"], ["1"], ["2"]], zebra_stripe=False)

        assert data.zebra_stripe is False

    def test_default_zebra_stripe(self):
        """Test default zebra stripe is False."""
        data = TableData(rows=[["A"], ["1"]])

        assert data.zebra_stripe is False


class TestCompactMode:
    """Tests for compact mode validation."""

    def test_compact_true(self):
        """Test compact mode enabled."""
        data = TableData(rows=[["A"], ["1"]], compact=True)

        assert data.compact is True

    def test_compact_false(self):
        """Test compact mode disabled."""
        data = TableData(rows=[["A"], ["1"]], compact=False)

        assert data.compact is False

    def test_default_compact(self):
        """Test default compact mode is False."""
        data = TableData(rows=[["A"], ["1"]])

        assert data.compact is False


class TestNumberFormat:
    """Tests for number format validation."""

    def test_number_format_valid(self):
        """Test valid number format."""
        data = TableData(
            rows=[["Name", "Amount", "Percent"], ["Alice", "1234.56", "0.15"]],
            number_format={1: "currency:USD", 2: "percent"},
        )

        assert data.number_format == {1: "currency:USD", 2: "percent"}

    def test_number_format_none(self):
        """Test None number format is valid."""
        data = TableData(rows=[["A", "B"], ["1", "2"]], number_format=None)

        assert data.number_format is None

    def test_number_format_currency(self):
        """Test currency format specification."""
        data = TableData(rows=[["A", "B"], ["1", "2"]], number_format={1: "currency:EUR"})

        assert data.number_format[1] == "currency:EUR"

    def test_number_format_decimal(self):
        """Test decimal format specification."""
        data = TableData(rows=[["A", "B"], ["1", "2"]], number_format={1: "decimal:2"})

        assert data.number_format[1] == "decimal:2"

    def test_number_format_accounting(self):
        """Test accounting format specification."""
        data = TableData(rows=[["A", "B"], ["1", "2"]], number_format={1: "accounting"})

        assert data.number_format[1] == "accounting"

    def test_invalid_column_index_negative(self):
        """Test invalid negative column index."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A", "B"], ["1", "2"]], number_format={-1: "currency:USD"})

        assert exc.value.error_code == "INVALID_NUMBER_FORMAT"

    def test_invalid_column_index_exceeds_count(self):
        """Test column index exceeds column count."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A", "B"], ["1", "2"]], number_format={5: "currency:USD"})

        assert exc.value.error_code == "INVALID_NUMBER_FORMAT"

    def test_invalid_format_spec(self):
        """Test invalid format specification."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A", "B"], ["1", "2"]], number_format={1: "invalid_format"})

        assert exc.value.error_code == "INVALID_NUMBER_FORMAT"

    def test_invalid_currency_code(self):
        """Test invalid currency code in format."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A", "B"], ["1", "2"]], number_format={1: "currency:INVALID"})

        assert exc.value.error_code == "INVALID_NUMBER_FORMAT"

    def test_multiple_columns_formatted(self):
        """Test multiple columns with different formats."""
        data = TableData(
            rows=[["Name", "Price", "Discount", "Quantity"], ["Item", "100", "0.1", "5"]],
            number_format={1: "currency:USD", 2: "percent", 3: "integer"},
        )

        assert data.number_format[1] == "currency:USD"
        assert data.number_format[2] == "percent"
        assert data.number_format[3] == "integer"

    def test_format_column_zero(self):
        """Test formatting column 0."""
        data = TableData(rows=[["100", "200"], ["300", "400"]], number_format={0: "currency:USD"})

        assert data.number_format[0] == "currency:USD"


class TestHeaderColor:
    """Tests for header color validation."""

    def test_valid_theme_color(self):
        """Test valid theme color for header."""
        data = TableData(rows=[["A"], ["1"]], header_color="blue")

        assert data.header_color == "blue"

    def test_valid_hex_color(self):
        """Test valid hex color for header."""
        data = TableData(rows=[["A"], ["1"]], header_color="#FF0000")

        assert data.header_color == "#FF0000"

    def test_none_header_color(self):
        """Test None header color is valid."""
        data = TableData(rows=[["A"], ["1"]], header_color=None)

        assert data.header_color is None

    def test_invalid_header_color(self):
        """Test invalid header color."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A"], ["1"]], header_color="invalid")

        assert exc.value.error_code == "INVALID_COLOR"


class TestStripeColor:
    """Tests for stripe color validation."""

    def test_valid_theme_color(self):
        """Test valid theme color for stripes."""
        data = TableData(rows=[["A"], ["1"], ["2"]], zebra_stripe=True, stripe_color="green")

        assert data.stripe_color == "green"

    def test_valid_hex_color(self):
        """Test valid hex color for stripes."""
        data = TableData(rows=[["A"], ["1"], ["2"]], zebra_stripe=True, stripe_color="#00FF00")

        assert data.stripe_color == "#00FF00"

    def test_none_stripe_color(self):
        """Test None stripe color is valid."""
        data = TableData(rows=[["A"], ["1"]], stripe_color=None)

        assert data.stripe_color is None

    def test_invalid_stripe_color(self):
        """Test invalid stripe color."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A"], ["1"]], stripe_color="invalid")

        assert exc.value.error_code == "INVALID_COLOR"


class TestHighlightRows:
    """Tests for row highlighting validation."""

    def test_valid_single_row_highlight(self):
        """Test highlighting single row."""
        data = TableData(rows=[["A"], ["1"], ["2"], ["3"]], highlight_rows={1: "blue"})

        assert data.highlight_rows == {1: "blue"}

    def test_valid_multiple_row_highlights(self):
        """Test highlighting multiple rows."""
        data = TableData(
            rows=[["A"], ["1"], ["2"], ["3"]],
            highlight_rows={1: "blue", 2: "red"},
        )

        assert data.highlight_rows[1] == "blue"
        assert data.highlight_rows[2] == "red"

    def test_highlight_row_with_hex_color(self):
        """Test row highlight with hex color."""
        data = TableData(rows=[["A"], ["1"], ["2"]], highlight_rows={1: "#FF0000"})

        assert data.highlight_rows[1] == "#FF0000"

    def test_none_highlight_rows(self):
        """Test None highlight_rows is valid."""
        data = TableData(rows=[["A"], ["1"]], highlight_rows=None)

        assert data.highlight_rows is None

    def test_invalid_row_index_negative(self):
        """Test negative row index is invalid."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A"], ["1"]], highlight_rows={-1: "blue"})

        assert exc.value.error_code == "INVALID_HIGHLIGHT"

    def test_invalid_row_index_exceeds_count(self):
        """Test row index exceeding row count."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A"], ["1"], ["2"]], highlight_rows={5: "blue"})

        assert exc.value.error_code == "INVALID_HIGHLIGHT"

    def test_invalid_row_color(self):
        """Test invalid color for row highlight."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A"], ["1"], ["2"]], highlight_rows={1: "invalid"})

        assert exc.value.error_code == "INVALID_COLOR"


class TestHighlightColumns:
    """Tests for column highlighting validation."""

    def test_valid_single_column_highlight(self):
        """Test highlighting single column."""
        data = TableData(rows=[["A", "B", "C"], ["1", "2", "3"]], highlight_columns={1: "orange"})

        assert data.highlight_columns == {1: "orange"}

    def test_valid_multiple_column_highlights(self):
        """Test highlighting multiple columns."""
        data = TableData(
            rows=[["A", "B", "C"], ["1", "2", "3"]],
            highlight_columns={0: "blue", 2: "green"},
        )

        assert data.highlight_columns[0] == "blue"
        assert data.highlight_columns[2] == "green"

    def test_highlight_column_with_hex_color(self):
        """Test column highlight with hex color."""
        data = TableData(rows=[["A", "B"], ["1", "2"]], highlight_columns={1: "#00FF00"})

        assert data.highlight_columns[1] == "#00FF00"

    def test_none_highlight_columns(self):
        """Test None highlight_columns is valid."""
        data = TableData(rows=[["A", "B"], ["1", "2"]], highlight_columns=None)

        assert data.highlight_columns is None

    def test_invalid_column_index_negative(self):
        """Test negative column index is invalid."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A", "B"], ["1", "2"]], highlight_columns={-1: "blue"})

        assert exc.value.error_code == "INVALID_HIGHLIGHT"

    def test_invalid_column_index_exceeds_count(self):
        """Test column index exceeding column count."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A", "B"], ["1", "2"]], highlight_columns={5: "blue"})

        assert exc.value.error_code == "INVALID_HIGHLIGHT"

    def test_invalid_column_color(self):
        """Test invalid color for column highlight."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["A", "B"], ["1", "2"]], highlight_columns={1: "invalid"})

        assert exc.value.error_code == "INVALID_COLOR"


class TestSortBy:
    """Tests for sort_by validation."""

    def test_sort_by_column_name(self):
        """Test valid sort by column name."""
        data = TableData(
            rows=[["Name", "Age"], ["Alice", "30"], ["Bob", "25"]], sort_by="Name"
        )

        assert data.sort_by == "Name"

    def test_sort_by_column_index(self):
        """Test valid sort by column index."""
        data = TableData(rows=[["Alice", "30"], ["Bob", "25"]], has_header=False, sort_by=0)

        assert data.sort_by == 0

    def test_sort_by_dict_with_order(self):
        """Test sort with order specification."""
        data = TableData(
            rows=[["Name", "Age"], ["Alice", "30"]],
            sort_by={"column": "Age", "order": "desc"},
        )

        assert data.sort_by["column"] == "Age"
        assert data.sort_by["order"] == "desc"

    def test_sort_by_multiple_columns(self):
        """Test multi-column sort."""
        data = TableData(
            rows=[["Name", "Age", "City"], ["Alice", "30", "NYC"]],
            sort_by=["Name", "Age"],
        )

        assert data.sort_by == ["Name", "Age"]

    def test_sort_by_column_name_without_header(self):
        """Test error when sorting by column name without header."""
        with pytest.raises(TableValidationError) as exc:
            TableData(
                rows=[["Alice", "30"], ["Bob", "25"]], has_header=False, sort_by="Name"
            )

        assert exc.value.error_code == "INVALID_SORT"
        assert "requires has_header=True" in exc.value.message

    def test_sort_by_invalid_column_name(self):
        """Test error for non-existent column name."""
        with pytest.raises(TableValidationError) as exc:
            TableData(
                rows=[["Name", "Age"], ["Alice", "30"]], sort_by="Salary"
            )

        assert exc.value.error_code == "INVALID_SORT"
        assert "not found in header row" in exc.value.message

    def test_sort_by_invalid_column_index(self):
        """Test error for out of range column index."""
        with pytest.raises(TableValidationError) as exc:
            TableData(
                rows=[["Alice", "30"], ["Bob", "25"]], has_header=False, sort_by=5
            )

        assert exc.value.error_code == "INVALID_SORT"
        assert "exceeds number of columns" in exc.value.message

    def test_sort_by_negative_index(self):
        """Test error for negative column index."""
        with pytest.raises(TableValidationError) as exc:
            TableData(
                rows=[["Alice", "30"], ["Bob", "25"]], has_header=False, sort_by=-1
            )

        assert exc.value.error_code == "INVALID_SORT"
        assert "must be non-negative" in exc.value.message

    def test_sort_by_invalid_order(self):
        """Test error for invalid sort order."""
        with pytest.raises(TableValidationError) as exc:
            TableData(
                rows=[["Name"], ["Alice"]],
                sort_by={"column": "Name", "order": "invalid"},
            )

        assert exc.value.error_code == "INVALID_SORT"
        assert "must be 'asc' or 'desc'" in exc.value.message

    def test_sort_by_dict_missing_column(self):
        """Test error when dict missing column key."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["Alice"]], has_header=False, sort_by={"order": "asc"})

        assert exc.value.error_code == "INVALID_SORT"
        assert "must have 'column' key" in exc.value.message

    def test_sort_by_invalid_type(self):
        """Test error for invalid sort_by type."""
        with pytest.raises(TableValidationError) as exc:
            TableData(rows=[["Alice"]], has_header=False, sort_by=3.14)

        assert exc.value.error_code == "INVALID_SORT"


class TestColumnWidths:
    """Tests for column_widths validation."""

    def test_valid_column_widths(self):
        """Test valid column widths."""
        data = TableData(
            rows=[["A", "B", "C"], ["1", "2", "3"]],
            has_header=False,
            column_widths={0: "30%", 1: "40%", 2: "30%"},
        )

        assert data.column_widths[0] == "30%"
        assert data.column_widths[1] == "40%"
        assert data.column_widths[2] == "30%"

    def test_partial_column_widths(self):
        """Test partial column widths (auto-distribute remaining)."""
        data = TableData(
            rows=[["A", "B", "C"], ["1", "2", "3"]],
            has_header=False,
            column_widths={0: "40%", 2: "30%"},
        )

        assert data.column_widths[0] == "40%"
        assert data.column_widths[2] == "30%"
        # Column 1 should auto-distribute (30% remaining)

    def test_column_widths_invalid_index(self):
        """Test error for invalid column index."""
        with pytest.raises(TableValidationError) as exc:
            TableData(
                rows=[["A", "B"], ["1", "2"]],
                has_header=False,
                column_widths={5: "50%"},
            )

        assert exc.value.error_code == "INVALID_COLUMN_WIDTH"
        assert "exceeds number of columns" in exc.value.message

    def test_column_widths_negative_index(self):
        """Test error for negative column index."""
        with pytest.raises(TableValidationError) as exc:
            TableData(
                rows=[["A", "B"], ["1", "2"]],
                has_header=False,
                column_widths={-1: "50%"},
            )

        assert exc.value.error_code == "INVALID_COLUMN_WIDTH"
        assert "must be a non-negative integer" in exc.value.message

    def test_column_widths_invalid_format(self):
        """Test error for invalid percentage format."""
        with pytest.raises(TableValidationError) as exc:
            TableData(
                rows=[["A", "B"], ["1", "2"]],
                has_header=False,
                column_widths={0: "50px"},
            )

        assert exc.value.error_code == "INVALID_COLUMN_WIDTH"
        assert "must be a percentage string" in exc.value.message

    def test_column_widths_invalid_percentage_value(self):
        """Test error for invalid percentage value."""
        with pytest.raises(TableValidationError) as exc:
            TableData(
                rows=[["A", "B"], ["1", "2"]],
                has_header=False,
                column_widths={0: "abc%"},
            )

        assert exc.value.error_code == "INVALID_COLUMN_WIDTH"
        assert "Invalid percentage format" in exc.value.message

    def test_column_widths_exceeds_100(self):
        """Test error when total widths exceed 100%."""
        with pytest.raises(TableValidationError) as exc:
            TableData(
                rows=[["A", "B"], ["1", "2"]],
                has_header=False,
                column_widths={0: "60%", 1: "50%"},
            )

        assert exc.value.error_code == "INVALID_COLUMN_WIDTH"
        assert "exceed 100%" in exc.value.message

    def test_column_widths_zero_percentage(self):
        """Test error for zero percentage."""
        with pytest.raises(TableValidationError) as exc:
            TableData(
                rows=[["A", "B"], ["1", "2"]],
                has_header=False,
                column_widths={0: "0%"},
            )

        assert exc.value.error_code == "INVALID_COLUMN_WIDTH"
        assert "must be between 0 and 100" in exc.value.message

    def test_column_widths_over_100_percent(self):
        """Test error for percentage over 100."""
        with pytest.raises(TableValidationError) as exc:
            TableData(
                rows=[["A", "B"], ["1", "2"]],
                has_header=False,
                column_widths={0: "150%"},
            )

        assert exc.value.error_code == "INVALID_COLUMN_WIDTH"
        assert "must be between 0 and 100" in exc.value.message
