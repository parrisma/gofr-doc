"""Tests for table sorting functionality."""

import pytest
from app.formatting.table_sorter import sort_table_rows


class TestSingleColumnSort:
    """Tests for single column sorting."""

    def test_sort_by_column_index_ascending(self):
        """Test sorting by column index in ascending order."""
        rows = [["Alice", "30"], ["Charlie", "25"], ["Bob", "35"]]

        sorted_rows = sort_table_rows(rows, 0, has_header=False)

        assert sorted_rows[0][0] == "Alice"
        assert sorted_rows[1][0] == "Bob"
        assert sorted_rows[2][0] == "Charlie"

    def test_sort_by_column_index_descending(self):
        """Test sorting by column index in descending order."""
        rows = [["Alice", "30"], ["Charlie", "25"], ["Bob", "35"]]

        sorted_rows = sort_table_rows(rows, {"column": 0, "order": "desc"}, has_header=False)

        assert sorted_rows[0][0] == "Charlie"
        assert sorted_rows[1][0] == "Bob"
        assert sorted_rows[2][0] == "Alice"

    def test_sort_by_column_name(self):
        """Test sorting by column name with header."""
        rows = [
            ["Name", "Age"],
            ["Alice", "30"],
            ["Charlie", "25"],
            ["Bob", "35"],
        ]

        sorted_rows = sort_table_rows(rows, "Name", has_header=True)

        # Header should remain first
        assert sorted_rows[0] == ["Name", "Age"]
        # Data sorted alphabetically
        assert sorted_rows[1][0] == "Alice"
        assert sorted_rows[2][0] == "Bob"
        assert sorted_rows[3][0] == "Charlie"

    def test_sort_numeric_column_ascending(self):
        """Test sorting numeric values in ascending order."""
        rows = [["Product", "Price"], ["A", "100"], ["B", "25"], ["C", "50"]]

        sorted_rows = sort_table_rows(rows, "Price", has_header=True)

        assert sorted_rows[0] == ["Product", "Price"]
        assert sorted_rows[1][1] == "25"
        assert sorted_rows[2][1] == "50"
        assert sorted_rows[3][1] == "100"

    def test_sort_numeric_column_descending(self):
        """Test sorting numeric values in descending order."""
        rows = [["Product", "Price"], ["A", "100"], ["B", "25"], ["C", "50"]]

        sorted_rows = sort_table_rows(rows, {"column": "Price", "order": "desc"}, has_header=True)

        assert sorted_rows[0] == ["Product", "Price"]
        assert sorted_rows[1][1] == "100"
        assert sorted_rows[2][1] == "50"
        assert sorted_rows[3][1] == "25"


class TestStringSort:
    """Tests for string sorting behavior."""

    def test_case_insensitive_sort(self):
        """Test case-insensitive string sorting."""
        rows = [["apple"], ["Banana"], ["APRICOT"], ["banana"]]

        sorted_rows = sort_table_rows(rows, 0, has_header=False)

        # Should sort: apple, APRICOT, Banana, banana
        assert sorted_rows[0][0] == "apple"
        assert sorted_rows[1][0] == "APRICOT"
        assert sorted_rows[2][0] in ["Banana", "banana"]  # Stable sort preserves order

    def test_string_with_numbers(self):
        """Test sorting strings that contain numbers."""
        rows = [["item10"], ["item2"], ["item1"]]

        sorted_rows = sort_table_rows(rows, 0, has_header=False)

        # Lexicographic sort: item1, item10, item2
        assert sorted_rows[0][0] == "item1"
        assert sorted_rows[1][0] == "item10"
        assert sorted_rows[2][0] == "item2"


class TestNumericSort:
    """Tests for numeric sorting behavior."""

    def test_integer_sort(self):
        """Test sorting integer values."""
        rows = [["10"], ["2"], ["100"], ["20"]]

        sorted_rows = sort_table_rows(rows, 0, has_header=False)

        assert sorted_rows[0][0] == "2"
        assert sorted_rows[1][0] == "10"
        assert sorted_rows[2][0] == "20"
        assert sorted_rows[3][0] == "100"

    def test_float_sort(self):
        """Test sorting float values."""
        rows = [["10.5"], ["2.1"], ["100.0"], ["20.9"]]

        sorted_rows = sort_table_rows(rows, 0, has_header=False)

        assert sorted_rows[0][0] == "2.1"
        assert sorted_rows[1][0] == "10.5"
        assert sorted_rows[2][0] == "20.9"
        assert sorted_rows[3][0] == "100.0"

    def test_comma_separated_numbers(self):
        """Test sorting numbers with comma separators."""
        rows = [["10,000"], ["2,500"], ["100,000"], ["5,000"]]

        sorted_rows = sort_table_rows(rows, 0, has_header=False)

        assert sorted_rows[0][0] == "2,500"
        assert sorted_rows[1][0] == "5,000"
        assert sorted_rows[2][0] == "10,000"
        assert sorted_rows[3][0] == "100,000"

    def test_mixed_numeric_types(self):
        """Test sorting mixed int and float values."""
        rows = [[10], [2.5], ["100"], ["20.5"]]

        sorted_rows = sort_table_rows(rows, 0, has_header=False)

        # All treated as numeric
        assert float(sorted_rows[0][0]) == 2.5
        assert float(sorted_rows[1][0]) == 10.0
        assert float(sorted_rows[2][0]) == 20.5
        assert float(sorted_rows[3][0]) == 100.0


class TestMultiColumnSort:
    """Tests for multi-column sorting."""

    def test_sort_two_columns(self):
        """Test sorting by two columns."""
        rows = [
            ["Name", "Age"],
            ["Alice", "30"],
            ["Bob", "25"],
            ["Alice", "25"],
            ["Bob", "30"],
        ]

        # Sort by Name, then Age
        sorted_rows = sort_table_rows(rows, ["Name", "Age"], has_header=True)

        assert sorted_rows[0] == ["Name", "Age"]
        assert sorted_rows[1] == ["Alice", "25"]
        assert sorted_rows[2] == ["Alice", "30"]
        assert sorted_rows[3] == ["Bob", "25"]
        assert sorted_rows[4] == ["Bob", "30"]

    def test_sort_mixed_order(self):
        """Test sorting with mixed ascending/descending."""
        rows = [
            ["Product", "Price", "Stock"],
            ["A", "100", "50"],
            ["B", "100", "30"],
            ["C", "50", "50"],
        ]

        # Sort by Price desc, then Stock asc
        sorted_rows = sort_table_rows(
            rows,
            [
                {"column": "Price", "order": "desc"},
                {"column": "Stock", "order": "asc"},
            ],
            has_header=True,
        )

        assert sorted_rows[0] == ["Product", "Price", "Stock"]
        assert sorted_rows[1] == ["B", "100", "30"]
        assert sorted_rows[2] == ["A", "100", "50"]
        assert sorted_rows[3] == ["C", "50", "50"]


class TestStableSort:
    """Tests for stable sorting behavior."""

    def test_preserve_order_for_equal_values(self):
        """Test that equal values maintain their original order."""
        rows = [
            ["Alice", "30", "X"],
            ["Bob", "30", "Y"],
            ["Charlie", "30", "Z"],
        ]

        sorted_rows = sort_table_rows(rows, 1, has_header=False)

        # All have same age, order should be preserved
        assert sorted_rows[0][2] == "X"
        assert sorted_rows[1][2] == "Y"
        assert sorted_rows[2][2] == "Z"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_table(self):
        """Test sorting empty table."""
        rows = []

        sorted_rows = sort_table_rows(rows, 0, has_header=False)

        assert sorted_rows == []

    def test_single_row_no_header(self):
        """Test sorting table with single row and no header."""
        rows = [["Alice", "30"]]

        sorted_rows = sort_table_rows(rows, 0, has_header=False)

        assert sorted_rows == [["Alice", "30"]]

    def test_header_only(self):
        """Test sorting table with header only."""
        rows = [["Name", "Age"]]

        sorted_rows = sort_table_rows(rows, "Name", has_header=True)

        assert sorted_rows == [["Name", "Age"]]

    def test_none_values(self):
        """Test sorting with None values."""
        rows = [["Alice"], [None], ["Bob"]]

        sorted_rows = sort_table_rows(rows, 0, has_header=False)

        # None should be treated as empty string
        assert sorted_rows[0][0] is None or sorted_rows[0][0] == ""
        assert "Alice" in [row[0] for row in sorted_rows]
        assert "Bob" in [row[0] for row in sorted_rows]


class TestValidation:
    """Tests for validation and error handling."""

    def test_invalid_column_name(self):
        """Test error for non-existent column name."""
        rows = [["Name", "Age"], ["Alice", "30"]]

        with pytest.raises(ValueError, match="Column 'Salary' not found"):
            sort_table_rows(rows, "Salary", has_header=True)

    def test_column_name_without_header(self):
        """Test error when using column name without header."""
        rows = [["Alice", "30"], ["Bob", "25"]]

        with pytest.raises(ValueError, match="requires has_header=True"):
            sort_table_rows(rows, "Name", has_header=False)

    def test_invalid_column_index(self):
        """Test error for out of range column index."""
        rows = [["Alice", "30"], ["Bob", "25"]]

        with pytest.raises(ValueError, match="Column index 5 out of range"):
            sort_table_rows(rows, 5, has_header=False)

    def test_invalid_sort_order(self):
        """Test error for invalid sort order."""
        rows = [["Name", "Age"], ["Alice", "30"]]

        with pytest.raises(ValueError, match="Sort order must be 'asc' or 'desc'"):
            sort_table_rows(rows, {"column": "Name", "order": "invalid"}, has_header=True)

    def test_invalid_sort_spec_type(self):
        """Test error for invalid sort specification type."""
        rows = [["Alice", "30"], ["Bob", "25"]]

        with pytest.raises(ValueError, match="Invalid sort specification"):
            sort_table_rows(rows, 3.14, has_header=False)

    def test_missing_column_key_in_dict(self):
        """Test error when dict is missing 'column' key."""
        rows = [["Alice", "30"], ["Bob", "25"]]

        with pytest.raises(ValueError, match="must have 'column' key"):
            sort_table_rows(rows, {"order": "asc"}, has_header=False)
