# Table Fragment User Guide

## Overview

The table fragment enables rich, formatted tables in documents with support for:
- Number formatting (currency, percentages, decimals)
- Column alignment and styling
- Theme colors and row/column highlighting
- Sorting and column width control
- Multiple output formats (HTML, PDF, Markdown)

## Quick Start

### Basic Table

```python
{
    "rows": [
        ["Name", "Age", "City"],
        ["Alice", "30", "New York"],
        ["Bob", "25", "Boston"]
    ],
    "has_header": True,
    "title": "Employee Directory"
}
```

### Financial Table with Formatting

```python
{
    "rows": [
        ["Quarter", "Revenue", "Growth"],
        ["Q1 2024", "1250000", "0.15"],
        ["Q2 2024", "1380000", "0.104"],
        ["Q3 2024", "1520000", "0.101"]
    ],
    "has_header": True,
    "title": "Quarterly Performance",
    "column_alignments": ["left", "right", "right"],
    "number_format": {
        "1": "currency:USD",
        "2": "percent"
    },
    "header_color": "primary",
    "zebra_stripe": True,
    "sort_by": {"column": "Revenue", "order": "desc"}
}
```

## Parameter Reference

### Core Parameters

#### `rows` (required)
**Type**: `array of arrays`  
**Description**: Table data as 2D array. First row becomes header if `has_header=true`.

```python
"rows": [
    ["Product", "Price", "Stock"],
    ["Widget", "29.99", "150"],
    ["Gadget", "49.99", "75"]
]
```

**Validation**:
- Must be non-empty
- All rows must have same column count
- Each row must be an array

#### `has_header` (optional)
**Type**: `boolean`  
**Default**: `false`  
**Description**: Treat first row as header (rendered in `<thead>`).

```python
"has_header": True
```

#### `title` (optional)
**Type**: `string`  
**Description**: Display title above table.

```python
"title": "Q4 2024 Sales Report"
```

#### `width` (optional)
**Type**: `string`  
**Default**: `"auto"`  
**Options**: `"auto"`, `"full"`, or percentage (e.g., `"80%"`)

```python
"width": "100%"  # Full width
"width": "auto"  # Fit content
"width": "60%"   # 60% of container
```

---

### Alignment & Styling

#### `column_alignments` (optional)
**Type**: `array of strings`  
**Options**: `"left"`, `"center"`, `"right"`  
**Description**: Set alignment for each column. Defaults to `"left"`.

```python
"column_alignments": ["left", "right", "center", "right"]
```

**Notes**:
- Array length can be less than column count (remaining columns default to left)
- Excess alignments are ignored
- Applies to both header and data cells

#### `border_style` (optional)
**Type**: `string`  
**Default**: `"full"`  
**Options**:
- `"full"` - All borders (top, right, bottom, left)
- `"horizontal"` - Top and bottom borders only
- `"minimal"` - Bottom border only
- `"none"` - No borders

```python
"border_style": "horizontal"
```

#### `zebra_stripe` (optional)
**Type**: `boolean`  
**Default**: `false`  
**Description**: Alternate row background colors.

```python
"zebra_stripe": True
```

#### `compact` (optional)
**Type**: `boolean`  
**Default**: `false`  
**Description**: Reduced cell padding for dense tables.

```python
"compact": True
```

---

### Number Formatting

#### `number_format` (optional)
**Type**: `object` (column index → format string)  
**Description**: Apply number formatting to specific columns (0-indexed).

**Format Options**:
- `"currency:CODE"` - Currency with 3-letter code (e.g., `"currency:USD"`, `"currency:EUR"`)
- `"percent"` - Percentage with 1 decimal (e.g., `15.5%`)
- `"decimal:N"` - N decimal places (e.g., `"decimal:2"` → `1,234.56`)
- `"integer"` - Whole numbers with thousand separators (e.g., `1,234`)
- `"accounting"` - Accounting format with parentheses for negatives

```python
"number_format": {
    "1": "currency:USD",    # Column 1: $1,234.56
    "2": "percent",         # Column 2: 15.5%
    "3": "decimal:2",       # Column 3: 1,234.56
    "4": "integer"          # Column 4: 1,234
}
```

**Examples**:

| Input | Format | Output |
|-------|--------|--------|
| `"1250000"` | `"currency:USD"` | `$1,250,000.00` |
| `"0.155"` | `"percent"` | `15.5%` |
| `"1234.5678"` | `"decimal:2"` | `1,234.57` |
| `"-500"` | `"accounting"` | `(500.00)` |

---

### Colors & Highlighting

#### `header_color` (optional)
**Type**: `string`  
**Description**: Background color for header row.

**Theme Colors**: `"primary"`, `"success"`, `"warning"`, `"danger"`, `"info"`, `"light"`, `"dark"`, `"muted"`  
**Hex Colors**: `"#FF5733"`, `"#3498db"`, etc.

```python
"header_color": "primary"
"header_color": "#2c3e50"
```

#### `stripe_color` (optional)
**Type**: `string`  
**Description**: Background color for alternate rows when `zebra_stripe=true`.

```python
"zebra_stripe": True,
"stripe_color": "light"
```

#### `highlight_rows` (optional)
**Type**: `object` (row index → color)  
**Description**: Highlight specific rows (0-indexed, excludes header).

```python
"highlight_rows": {
    "0": "warning",    # First data row
    "3": "#ffe6e6"     # Fourth data row
}
```

**Note**: Row highlighting overrides zebra striping for that row.

#### `highlight_columns` (optional)
**Type**: `object` (column index → color)  
**Description**: Highlight specific columns (0-indexed).

```python
"highlight_columns": {
    "2": "info",       # Third column
    "4": "#e6f3ff"     # Fifth column
}
```

---

### Advanced Features

#### `sort_by` (optional)
**Type**: `string`, `integer`, or `object`  
**Description**: Sort table by column.

**Simple Sort** (ascending):
```python
"sort_by": "Revenue"          # By column name
"sort_by": 1                  # By column index
```

**Sort with Order**:
```python
"sort_by": {
    "column": "Revenue",       # or column index
    "order": "desc"            # "asc" or "desc"
}
```

**Multi-Column Sort**:
```python
"sort_by": [
    {"column": "Category", "order": "asc"},
    {"column": "Revenue", "order": "desc"}
]
```

**Notes**:
- Numeric detection: Values like `"1,234.56"` are sorted numerically
- Column names require `has_header=true`
- Sorting happens before rendering

#### `column_widths` (optional)
**Type**: `object` (column index → width)  
**Description**: Set specific column widths (0-indexed).

**Percentage Widths**:
```python
"column_widths": {
    "0": "30%",
    "1": "20%",
    "2": "50%"
}
```

**Pixel Widths**:
```python
"column_widths": {
    "0": "200px",
    "1": "150px"
}
```

**Notes**:
- Percentages should sum to ≤ 100%
- Partial specification allowed (unspecified columns auto-size)
- Uses HTML `<colgroup>` for width control

---

## Output Formats

### HTML
Full feature support including colors, borders, and styling.

```python
{
    "output_format": "html",
    "style_id": "default"
}
```

### PDF
Full feature support. Colors and formatting preserved in PDF.

```python
{
    "output_format": "pdf",
    "style_id": "default"
}
```

### Markdown
Limited feature support:
- ✅ Table structure, headers, data
- ✅ Column alignment markers (`:---`, `:---:`, `---:`)
- ✅ Number formatting preserved in cells
- ❌ Colors, borders, highlighting (not supported in Markdown)

```python
{
    "output_format": "markdown"
}
```

**Example Markdown Output**:
```markdown
| Name  | Revenue    | Growth |
| :---- | ---------: | -----: |
| Alice | $1,250,000 |  15.5% |
| Bob   | $1,380,000 |  10.4% |
```

---

## Complete Examples

### Example 1: Simple Data Table

```python
{
    "fragment_id": "employees",
    "parameters": {
        "rows": [
            ["Name", "Department", "Years"],
            ["Alice Johnson", "Engineering", "5"],
            ["Bob Smith", "Marketing", "3"],
            ["Carol White", "Sales", "7"]
        ],
        "has_header": True,
        "title": "Employee Directory",
        "width": "100%",
        "column_alignments": ["left", "left", "center"],
        "zebra_stripe": True
    }
}
```

### Example 2: Financial Report

```python
{
    "fragment_id": "quarterly_results",
    "parameters": {
        "rows": [
            ["Quarter", "Revenue", "Expenses", "Profit", "Margin"],
            ["Q1 2024", "1250000", "850000", "400000", "0.32"],
            ["Q2 2024", "1380000", "920000", "460000", "0.33"],
            ["Q3 2024", "1520000", "980000", "540000", "0.36"],
            ["Q4 2024", "1650000", "1050000", "600000", "0.36"]
        ],
        "has_header": True,
        "title": "2024 Financial Performance",
        "width": "100%",
        "column_alignments": ["left", "right", "right", "right", "right"],
        "border_style": "full",
        "zebra_stripe": True,
        "number_format": {
            "1": "currency:USD",
            "2": "currency:USD",
            "3": "currency:USD",
            "4": "percent"
        },
        "header_color": "primary",
        "stripe_color": "light",
        "highlight_columns": {
            "3": "success"
        },
        "sort_by": {"column": "Revenue", "order": "desc"},
        "column_widths": {
            "0": "20%",
            "1": "20%",
            "2": "20%",
            "3": "20%",
            "4": "20%"
        }
    }
}
```

### Example 3: Product Comparison

```python
{
    "fragment_id": "products",
    "parameters": {
        "rows": [
            ["Product", "Price", "Rating", "Stock", "Status"],
            ["Widget Pro", "299.99", "4.8", "150", "In Stock"],
            ["Gadget Plus", "199.99", "4.5", "75", "Low Stock"],
            ["Device Elite", "399.99", "4.9", "200", "In Stock"],
            ["Tool Master", "149.99", "4.2", "5", "Low Stock"]
        ],
        "has_header": True,
        "title": "Product Inventory",
        "column_alignments": ["left", "right", "center", "right", "center"],
        "border_style": "horizontal",
        "compact": True,
        "number_format": {
            "1": "currency:USD",
            "2": "decimal:1"
        },
        "header_color": "#2c3e50",
        "highlight_rows": {
            "1": "warning",  # Low stock items
            "3": "warning"
        },
        "sort_by": {"column": "Rating", "order": "desc"}
    }
}
```

---

## Common Patterns

### Pattern 1: Top Performers Table
Highlight top rows, sort descending:

```python
{
    "sort_by": {"column": "Sales", "order": "desc"},
    "highlight_rows": {
        "0": "success",
        "1": "success",
        "2": "success"
    }
}
```

### Pattern 2: Comparison Table
Highlight specific column for easy comparison:

```python
{
    "highlight_columns": {"3": "info"},
    "column_widths": {
        "0": "30%",
        "1": "20%",
        "2": "20%",
        "3": "30%"
    }
}
```

### Pattern 3: Compact Wide Table
Many columns with reduced padding:

```python
{
    "compact": True,
    "border_style": "minimal",
    "width": "100%"
}
```

---

## Error Handling

### Common Validation Errors

**ERR001: Empty rows**
```
Error: Table rows cannot be empty
Fix: Provide at least one row of data
```

**ERR002: Inconsistent column count**
```
Error: All rows must have the same number of columns
Fix: Ensure every row has exactly N columns
```

**ERR003: Invalid alignment**
```
Error: Column alignment must be 'left', 'center', or 'right'
Fix: Use only valid alignment values
```

**ERR004: Invalid number format**
```
Error: Number format must be 'currency:CODE', 'percent', 'decimal:N', 'integer', or 'accounting'
Fix: Use valid format string (e.g., "currency:USD", "decimal:2")
```

**ERR005: Invalid color**
```
Error: Color must be a theme color or hex code
Fix: Use theme color (primary, success, etc.) or hex code (#RRGGBB)
```

**ERR006: Column index out of range**
```
Error: Column index exceeds table width
Fix: Ensure column indices are within 0 to (column_count - 1)
```

**ERR007: Row index out of range**
```
Error: Row index exceeds table height
Fix: Ensure row indices are within valid range (excluding header)
```

**ERR008: Invalid sort column**
```
Error: Sort column does not exist
Fix: Use valid column name (requires has_header=true) or column index
```

**ERR009: Invalid width format**
```
Error: Column width must be percentage (e.g., '30%') or pixels (e.g., '200px')
Fix: Use valid width format
```

**ERR010: Widths exceed 100%**
```
Error: Total column widths exceed 100%
Fix: Ensure percentages sum to ≤ 100%
```

---

## Best Practices

### 1. Performance
- Large tables (100+ rows): Use `compact=true` to reduce HTML size
- Wide tables (20+ columns): Consider horizontal scrolling container
- Sorting: Pre-sort data when possible to avoid runtime sorting

### 2. Readability
- Use `zebra_stripe=true` for tables with many rows
- Apply `compact=false` (default) for tables with dense text
- Use column alignment to improve number readability (right-align numbers)

### 3. Accessibility
- Always use `has_header=true` for semantic HTML
- Provide descriptive `title` for table context
- Use high-contrast colors for better visibility

### 4. Formatting
- Currency: Always specify currency code (`"currency:USD"`)
- Percentages: Input as decimals (0.15 → 15%)
- Large numbers: Use integer or decimal formatting for readability

### 5. Color Usage
- Limit highlights to important rows/columns (3-5 maximum)
- Use theme colors for consistency across documents
- Avoid red/green combinations (colorblind-friendly)

---

## Dependencies

- **Babel >= 2.13.0**: Required for number/currency formatting
- **Jinja2**: Template rendering
- **WeasyPrint**: PDF generation
- **html2text**: Markdown conversion

Install:
```bash
pip install Babel>=2.13.0
```

---

## Technical Notes

### Rendering Pipeline

1. **Validation**: Parameters validated via `TableData` Pydantic model
2. **Sorting**: Applied before rendering if `sort_by` specified
3. **Formatting**: Numbers formatted via Babel during template rendering
4. **Template**: Jinja2 template renders HTML with all features
5. **Conversion**: 
   - HTML: Direct output
   - PDF: WeasyPrint converts HTML → PDF
   - Markdown: html2text converts HTML → Markdown with alignment enhancement

### Markdown Limitations

Markdown has limited table support:
- No colors or background styling
- No border control
- No cell padding control
- Alignment markers may not render in all Markdown viewers

Use HTML or PDF formats when rich styling is required.

---

## Version History

- **v1.0** (Nov 2024): Initial release with all 14 parameters
  - Basic structure (rows, has_header, title, width)
  - Alignment & styling (column_alignments, border_style, zebra_stripe, compact)
  - Number formatting (currency, percent, decimal, integer, accounting)
  - Colors (header_color, stripe_color, highlight_rows, highlight_columns)
  - Advanced features (sort_by, column_widths)
  - Markdown support with alignment markers
