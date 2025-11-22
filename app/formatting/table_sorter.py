"""Table sorting functionality for sorting rows by column values."""

from typing import List, Union, Dict, Any, Tuple


def _is_numeric(value: Any) -> bool:
    """
    Check if a value can be treated as numeric.

    Args:
        value: Value to check

    Returns:
        True if value is numeric or can be converted to float
    """
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value.replace(",", ""))  # Handle comma-separated numbers
            return True
        except (ValueError, AttributeError):
            return False
    return False


def _to_numeric(value: Any) -> float:
    """
    Convert a value to numeric for sorting.

    Args:
        value: Value to convert

    Returns:
        Float representation of value
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove commas for thousand separators
        return float(value.replace(",", ""))
    return 0.0


def sort_table_rows(
    rows: List[List[Any]],
    sort_by: Union[str, int, Dict[str, str], List[Union[str, int, Dict[str, str]]]],
    has_header: bool = False,
) -> List[List[Any]]:
    """
    Sort table rows by one or more columns.

    Args:
        rows: Table rows (including header if has_header=True)
        sort_by: Column specification(s):
            - str: Column name (requires has_header=True)
            - int: Column index (0-based)
            - dict: {"column": name_or_index, "order": "asc"|"desc"}
            - list: Multiple sort specifications for multi-column sort
        has_header: Whether first row is a header row

    Returns:
        Sorted table rows (header row in same position if present)

    Raises:
        ValueError: If sort_by is invalid or column doesn't exist

    Examples:
        >>> rows = [["Name", "Age"], ["Bob", "25"], ["Alice", "30"]]
        >>> sort_table_rows(rows, "Name", has_header=True)
        [["Name", "Age"], ["Alice", "30"], ["Bob", "25"]]

        >>> rows = [["A", "B"], ["2", "X"], ["1", "Y"]]
        >>> sort_table_rows(rows, 0, has_header=True)
        [["A", "B"], ["1", "Y"], ["2", "X"]]

        >>> sort_table_rows(rows, {"column": 0, "order": "desc"}, has_header=True)
        [["A", "B"], ["2", "X"], ["1", "Y"]]
    """
    if not rows:
        return rows

    # Separate header if present
    header_row = rows[0] if has_header else None
    data_rows = rows[1:] if has_header else rows

    if not data_rows:
        return rows

    # Normalize sort_by to list of dicts
    if not isinstance(sort_by, list):
        sort_by = [sort_by]

    # Convert to list of (column_index, is_descending) tuples
    sort_specs: List[Tuple[int, bool]] = []

    for spec in sort_by:
        if isinstance(spec, str):
            # Column name - requires header
            if not has_header or not header_row:
                raise ValueError("Column name sorting requires has_header=True")
            try:
                col_idx = header_row.index(spec)
            except ValueError:
                raise ValueError(f"Column '{spec}' not found in header row")
            sort_specs.append((col_idx, False))  # Default ascending

        elif isinstance(spec, int):
            # Column index
            if spec < 0 or spec >= len(data_rows[0]):
                raise ValueError(f"Column index {spec} out of range (0-{len(data_rows[0])-1})")
            sort_specs.append((spec, False))  # Default ascending

        elif isinstance(spec, dict):
            # Dict with column and order
            if "column" not in spec:
                raise ValueError("Sort specification dict must have 'column' key")

            col = spec["column"]
            order = spec.get("order", "asc").lower()

            if order not in ["asc", "desc"]:
                raise ValueError(f"Sort order must be 'asc' or 'desc', got '{order}'")

            is_desc = order == "desc"

            # Resolve column to index
            if isinstance(col, str):
                if not has_header or not header_row:
                    raise ValueError("Column name sorting requires has_header=True")
                try:
                    col_idx = header_row.index(col)
                except ValueError:
                    raise ValueError(f"Column '{col}' not found in header row")
            elif isinstance(col, int):
                if col < 0 or col >= len(data_rows[0]):
                    raise ValueError(f"Column index {col} out of range (0-{len(data_rows[0])-1})")
                col_idx = col
            else:
                raise ValueError(f"Column must be string or int, got {type(col)}")

            sort_specs.append((col_idx, is_desc))
        else:
            raise ValueError(f"Invalid sort specification: {spec}")

    # For string descending, we need custom comparison
    # Build a comparison function that handles mixed asc/desc for strings
    def compare_rows(row):
        keys = []
        for col_idx, is_desc in sort_specs:
            if col_idx >= len(row):
                keys.append((0, 0 if not is_desc else float("inf")))
                continue

            value = row[col_idx]

            if _is_numeric(value):
                num_val = _to_numeric(value)
                keys.append((0, -num_val if is_desc else num_val))
            else:
                # For strings, use tuple of inverted characters for descending
                str_val = str(value).lower() if value is not None else ""
                if is_desc:
                    # Invert string by mapping each char - using negative ord won't work
                    # Use a large number minus ord to reverse sort order
                    keys.append((1, tuple(-ord(c) for c in str_val)))
                else:
                    keys.append((1, str_val))
        return tuple(keys)

    # Sort data rows using stable sort
    sorted_rows = sorted(data_rows, key=compare_rows)

    # Reconstruct with header if present
    if has_header and header_row:
        return [header_row] + sorted_rows
    return sorted_rows
