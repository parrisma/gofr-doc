# Table Fragment Design - Tabular Data with Formatting

## Overview
New fragment type `table` for adding formatted tabular data to documents. Supports column alignment, header styling, and alternating row colors without being overly complex.

## Design Principles
- **Simple API**: Pass data as array of rows (array of arrays)
- **Header Detection**: First row treated as header by default
- **Basic Formatting**: Column alignment, zebra striping, borders
- **Format-Agnostic**: Renders appropriately in HTML, PDF, and Markdown
- **No Complex Features**: No cell merging, nested tables, or advanced layouts

## Fragment Specification

### Fragment ID
`table`

### Description
Add a table with optional header row and column formatting. Supports column alignment and visual styling.

### Input Parameters

```yaml
parameters:
  - name: rows
    type: array
    description: "Array of rows, where each row is an array of cell values. First row is header by default."
    required: true
    example: [["Name", "Age", "City"], ["Alice", "30", "NYC"], ["Bob", "25", "LA"]]

  - name: has_header
    type: boolean
    description: "If true (default), first row is treated as header with bold styling"
    required: false
    default: true

  - name: column_alignments
    type: array
    description: "Array of alignment strings for each column: 'left', 'center', 'right'. Default: 'left' for all"
    required: false
    example: ["left", "right", "center"]

  - name: title
    type: string
    description: "Optional table caption/title displayed above the table"
    required: false

  - name: zebra_stripe
    type: boolean
    description: "If true (default), alternate row background colors for readability"
    required: false
    default: true

  - name: border_style
    type: string
    description: "Border style: 'full' (all borders), 'horizontal' (horizontal only), 'minimal' (header only), 'none'"
    required: false
    default: "full"
    enum: ["full", "horizontal", "minimal", "none"]

  - name: compact
    type: boolean
    description: "If true, reduce padding for more compact display"
    required: false
    default: false

  - name: width
    type: string
    description: "Table width: 'auto' (content-based), 'full' (100%), or specific value like '80%'"
    required: false
    default: "auto"

  - name: number_format
    type: object
    description: "Per-column number formatting configuration for financial/numeric data"
    required: false
    properties:
      column_index:
        type: string
        description: "Format specification: 'currency:USD', 'currency:EUR', 'percent', 'decimal:2', 'integer', 'accounting'"
    example: {"1": "currency:USD", "2": "percent", "3": "decimal:2"}

  - name: header_color
    type: string
    description: "Header row background color from theme palette or custom hex. Theme colors: 'blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink', 'gray', or custom '#RRGGBB'"
    required: false
    default: "blue"

  - name: stripe_color
    type: string
    description: "Alternate row background color for zebra striping. Theme colors or custom hex. Default: light gray"
    required: false
    default: "auto"

  - name: highlight_rows
    type: object
    description: "Highlight specific rows with theme colors. Keys are row indices (0-based, excluding header), values are theme color names"
    required: false
    example: {"2": "green", "5": "red"}

  - name: highlight_columns
    type: object
    description: "Highlight specific columns with theme colors. Keys are column indices (0-based), values are theme color names"
    required: false
    example: {"3": "orange", "4": "purple"}

  - name: sort_by
    type: array
    description: "Sort rows by column headers (ascending by default). Array of column names or objects with {column: name, order: 'asc'|'desc'}. Applies to data rows only (header excluded)"
    required: false
    example: ["Revenue", {"column": "Growth", "order": "desc"}]

  - name: column_widths
    type: object
    description: "Specify column widths as percentages. Keys are column indices (0-based), values are percentage strings. Remaining width distributed equally to other columns"
    required: false
    example: {"0": "30%", "1": "20%", "2": "20%", "3": "15%", "4": "15%"}
```

## Data Structure Examples

### Simple Table
```python
{
  "rows": [
    ["Product", "Price", "Stock"],
    ["Widget", "$19.99", "50"],
    ["Gadget", "$29.99", "23"],
    ["Doohickey", "$9.99", "100"]
  ]
}
```

### With Formatting, Colors, and Sorting
```python
{
  "rows": [
    ["Region", "Revenue", "Growth", "Expenses", "Profit"],
    ["North", "1200000", "0.15", "900000", "300000"],
    ["South", "1500000", "0.25", "950000", "550000"],
    ["East", "1800000", "0.20", "1000000", "800000"],
    ["West", "2100000", "0.17", "1050000", "1050000"]
  ],
  "title": "Regional Performance (Sorted by Revenue)",
  "column_alignments": ["left", "right", "right", "right", "right"],
  "number_format": {
    "1": "currency:USD",
    "2": "percent",
    "3": "currency:USD",
    "4": "currency:USD"
  },
  "zebra_stripe": true,
  "border_style": "horizontal",
  "header_color": "blue",
  "sort_by": [{"column": "Revenue", "order": "desc"}],  # Sort by revenue descending
  "column_widths": {
    "0": "20%",   # Region column
    "1": "20%",   # Revenue column
    "2": "15%",   # Growth column
    "3": "20%",   # Expenses column
    "4": "25%"    # Profit column
  }
}
```

### No Header Table
```python
{
  "rows": [
    ["Name:", "Alice Johnson"],
    ["Email:", "alice@example.com"],
    ["Phone:", "+1-555-0123"]
  ],
  "has_header": false,
  "column_alignments": ["right", "left"],
  "border_style": "minimal",
  "width": "60%"
}
```

## Rendering Strategy

### HTML Output
- Semantic `<table>` with `<thead>` and `<tbody>`
- CSS classes for styling: `.doco-table`, `.header-row`, `.zebra-stripe`
- Inline styles for alignment
- Responsive: horizontal scroll on small screens

### PDF Output
- Same HTML structure (rendered via HTML template)
- Fixed-width table with appropriate column sizing
- Print-friendly styling

### Markdown Output
- Standard Markdown table syntax with pipes
- Column alignment using `:---:`, `---:`, `:---`
- Title as text line above table
- Limitation: Zebra striping not available (Markdown constraint)

## Implementation Notes

### Validation
- Validate `rows` is non-empty array of arrays
- Validate all rows have same number of columns
- Validate column_alignments length matches column count (if provided)
- Validate alignment values are valid: 'left', 'center', 'right'
- Validate border_style is valid enum value
- Validate number_format keys are valid column indices (0-based integers)
- Validate number_format values match supported formats: `currency:CODE`, `percent`, `decimal:N`, `integer`, `accounting`
- Validate currency codes are valid ISO 4217 codes (USD, EUR, GBP, JPY, etc.)
- Validate header_color is theme color name or valid hex color
- Validate stripe_color is theme color name, 'auto', or valid hex color
- Validate highlight_rows keys are valid row indices (0-based, excluding header if has_header=true)
- Validate highlight_columns keys are valid column indices (0-based)
- Validate all color values are valid theme color names or hex format
- Validate sort_by column names exist in header row (if has_header=true)
- Validate sort_by order values are 'asc' or 'desc'
- Validate column_widths keys are valid column indices (0-based)
- Validate column_widths values are valid percentages (format: "N%" where N is 1-100)
- Validate column_widths total doesn't exceed 100%

### Error Handling
```python
# Error codes:
- INVALID_TABLE_DATA: rows not an array or empty
- INCONSISTENT_COLUMNS: rows have different column counts
- INVALID_ALIGNMENT: invalid alignment value or count mismatch
- INVALID_BORDER_STYLE: border_style not in enum
- INVALID_NUMBER_FORMAT: number_format key not a valid column index
- INVALID_FORMAT_SPEC: format specification invalid (e.g., "currency:XYZ", "decimal:abc")
- INVALID_CURRENCY_CODE: currency code not a valid ISO 4217 code
- INVALID_COLOR: color not a valid theme color name or hex format
- INVALID_ROW_INDEX: highlight_rows key exceeds row count
- INVALID_COLUMN_INDEX: highlight_columns key exceeds column count
- INVALID_SORT_COLUMN: sort_by column name not found in header row
- INVALID_SORT_ORDER: sort order not 'asc' or 'desc'
- INVALID_COLUMN_WIDTH: column_widths value not valid percentage format
- COLUMN_WIDTHS_EXCEED_100: sum of column_widths exceeds 100%
- SORT_REQUIRES_HEADER: sort_by specified but has_header=false
```

### Template Files
- `table.html.jinja2` - HTML/PDF rendering with number formatting and theme colors
- `table.md.jinja2` - Markdown rendering (optional, can use same template with format detection)

### Number Formatting Implementation
- Create `app/formatting/number_formatter.py` module
- Support locale-aware formatting (use Python's `locale` or `babel` library)
- Format numbers at template render time (Jinja2 custom filter)
- Preserve raw values in data structure (format is presentation-only)
- Handle edge cases: NaN, Infinity, non-numeric strings

### Theme Color Integration
- Access theme CSS variables at render time: `var(--doco-blue)`, `var(--doco-green)`, etc.
- **Theme Color Names**: `blue`, `orange`, `green`, `red`, `purple`, `brown`, `pink`, `gray`
- **Color Resolution**: 
  - Theme color names → CSS variable: `blue` → `var(--doco-blue)`
  - Hex colors → Direct value: `#FF5733` → `#FF5733`
  - `auto` for stripe_color → Use theme's default light background
- **Application**:
  - Header row: `background-color: var(--doco-{color}); color: white;`
  - Highlighted rows/columns: Semi-transparent overlay: `rgba({color}, 0.1)`
  - Zebra stripes: Light gray or theme-specific alternate background
- **Fallback**: If theme doesn't define color variable, use sensible defaults

### Sorting Implementation
- **Sort Order**: Sort data rows (excluding header) by specified column(s)
- **Multi-column Sort**: Apply sorts in array order (primary, secondary, etc.)
- **Sort Key**: 
  - Column name (string) → ascending sort
  - Object `{column: "Name", order: "desc"}` → explicit order
- **Numeric Detection**: Auto-detect numeric columns and sort numerically
- **Case-Insensitive**: String sorting is case-insensitive
- **Stability**: Preserve original order for equal values
- **Pre-format Sort**: Sort on raw values before number formatting applied

### Column Width Implementation
- **Width Specification**: Percentage strings (e.g., "25%")
- **HTML/PDF**: Use `<col>` tags with width attributes or inline styles
- **Markdown**: Width hints not supported (Markdown limitation)
- **Auto-distribute**: Columns without explicit widths share remaining percentage equally
- **Example**: 5 columns, widths {"0": "30%", "2": "20%"} → remaining 50% split across columns 1, 3, 4 (16.67% each)

## Number Formatting (Financial Data)

### Supported Format Specifications
- **`currency:USD`** - US Dollar: $1,234.56
- **`currency:EUR`** - Euro: €1.234,56
- **`currency:GBP`** - British Pound: £1,234.56
- **`currency:JPY`** - Japanese Yen: ¥1,235 (no decimals)
- **`percent`** - Percentage: 15.5% (input 0.155)
- **`decimal:N`** - Fixed decimals: 1,234.57 (N=2)
- **`integer`** - No decimals: 1,235
- **`accounting`** - Accounting style: (1,234.56) for negatives

### Format Behavior
- Numbers formatted at render time (stored as numeric strings)
- Non-numeric values passed through unchanged
- Empty cells remain empty
- Applies to entire column (specified by index, 0-based)
- Multiple columns can have different formats

### Financial Data Example
```python
{
  "rows": [
    ["Account", "Revenue", "Expenses", "Profit", "Margin"],
    ["Operations", "2500000", "1800000", "700000", "0.28"],
    ["Sales", "3200000", "2100000", "1100000", "0.34"],
    ["Marketing", "1500000", "1300000", "200000", "0.13"]
  ],
  "title": "Financial Summary - Q4 2024",
  "column_alignments": ["left", "right", "right", "right", "right"],
  "number_format": {
    "1": "currency:USD",      # Revenue column
    "2": "currency:USD",      # Expenses column  
    "3": "accounting",        # Profit (show negatives as (amount))
    "4": "percent"            # Margin as percentage
  },
  "zebra_stripe": true,
  "border_style": "horizontal",
  "width": "full"
}
# Renders as:
# | Account    |    Revenue |   Expenses |      Profit | Margin |
# |------------|------------|------------|-------------|--------|
# | Operations | $2,500,000 | $1,800,000 |    $700,000 | 28.0%  |
# | Sales      | $3,200,000 | $2,100,000 |  $1,100,000 | 34.0%  |
# | Marketing  | $1,500,000 | $1,300,000 |    $200,000 | 13.0%  |
```

## Usage Examples

### Via MCP Tool
```python
# Add simple table
await session.call_tool("add_fragment", {
    "session_id": session_id,
    "fragment_id": "table",
    "parameters": {
        "rows": [
            ["Name", "Score", "Grade"],
            ["Alice", "95", "A"],
            ["Bob", "87", "B"],
            ["Charlie", "92", "A-"]
        ],
        "column_alignments": ["left", "center", "center"]
    }
})

# Add financial table with number formatting
await session.call_tool("add_fragment", {
    "session_id": session_id,
    "fragment_id": "table",
    "parameters": {
        "title": "Sales Summary",
        "rows": [
            ["Region", "Q1", "Q2", "Q3", "Q4"],
            ["North", "120000", "135000", "142000", "155000"],
            ["South", "98000", "105000", "112000", "125000"],
            ["East", "88000", "92000", "98000", "103000"],
            ["West", "145000", "158000", "165000", "178000"]
        ],
        "column_alignments": ["left", "right", "right", "right", "right"],
        "number_format": {
            "1": "currency:USD",
            "2": "currency:USD",
            "3": "currency:USD",
            "4": "currency:USD"
        },
        "border_style": "horizontal",
        "width": "full"
    }
})

# Accounting format example (negative numbers)
await session.call_tool("add_fragment", {
    "session_id": session_id,
    "fragment_id": "table",
    "parameters": {
        "title": "P&L Statement",
        "rows": [
            ["Line Item", "Amount", "Change"],
            ["Revenue", "5000000", "0.15"],
            ["COGS", "-3000000", "-0.12"],
            ["Gross Profit", "2000000", "0.35"],
            ["Operating Expenses", "-1500000", "0.08"],
            ["Net Income", "500000", "0.45"]
        ],
        "column_alignments": ["left", "right", "right"],
        "number_format": {
            "1": "accounting",    # Shows negatives as (amount)
            "2": "percent"         # Change as percentage
        }
    }
})

# Financial table with theme colors, highlights, sorting, and column widths
await session.call_tool("add_fragment", {
    "session_id": session_id,
    "fragment_id": "table",
    "parameters": {
        "title": "Regional Performance Dashboard",
        "rows": [
            ["Region", "Revenue", "Target", "Achievement", "Status"],
            ["North", "2500000", "2000000", "1.25", "Exceeds"],
            ["South", "1800000", "2000000", "0.90", "Below"],
            ["East", "2200000", "2000000", "1.10", "Meets"],
            ["West", "3100000", "3000000", "1.03", "Meets"]
        ],
        "column_alignments": ["left", "right", "right", "right", "center"],
        "number_format": {
            "1": "currency:USD",
            "2": "currency:USD",
            "3": "decimal:2"
        },
        "header_color": "blue",
        "highlight_rows": {
            "0": "green",               # North (after sorting) in green
            "1": "red"                  # South (after sorting) in red
        },
        "highlight_columns": {
            "4": "orange"               # Status column in orange
        },
        "sort_by": [
            {"column": "Revenue", "order": "desc"}  # Sort by revenue descending
        ],
        "column_widths": {
            "0": "20%",   # Region
            "1": "25%",   # Revenue
            "2": "20%",   # Target
            "3": "15%",   # Achievement
            "4": "20%"    # Status
        },
        "zebra_stripe": true,
        "border_style": "horizontal"
    }
})

# Multi-column sorting example
await session.call_tool("add_fragment", {
    "session_id": session_id,
    "fragment_id": "table",
    "parameters": {
        "title": "Employee Roster (Sorted by Department, then Salary)",
        "rows": [
            ["Name", "Department", "Salary", "Hire Date"],
            ["Alice", "Engineering", "120000", "2020-01-15"],
            ["Bob", "Sales", "95000", "2019-05-20"],
            ["Charlie", "Engineering", "115000", "2021-03-10"],
            ["Diana", "Sales", "105000", "2018-11-05"],
            ["Eve", "Engineering", "125000", "2019-08-22"]
        ],
        "column_alignments": ["left", "left", "right", "center"],
        "number_format": {
            "2": "currency:USD"
        },
        "sort_by": [
            "Department",                           # Primary sort: Department (asc)
            {"column": "Salary", "order": "desc"}   # Secondary sort: Salary (desc)
        ],
        "column_widths": {
            "0": "30%",   # Name
            "1": "25%",   # Department
            "2": "25%",   # Salary
            "3": "20%"    # Hire Date
        }
    }
})
```

## Future Enhancements (Explicitly Out of Scope)
These are intentionally NOT included to keep the implementation simple:
- ❌ Cell merging/spanning
- ❌ Nested tables
- ❌ Per-cell formatting (bold, color, background)
- ❌ Sortable columns
- ❌ Dynamic filtering
- ❌ Formulas or calculations
- ❌ Cell validation
- ❌ Data import from CSV/Excel
- ❌ Column resizing
- ❌ Cell editing

**Rationale**: This is a document generation system, not a spreadsheet. Keep tables simple and presentational.

## Comparison with Image Fragment
- **Similarity**: Both are content fragments added via add_fragment
- **Difference**: Tables have no async validation (data is inline, not external)
- **Difference**: Tables are pure data (no URL fetching required)
- **Implementation**: Simpler - just template rendering with validation

## Test Coverage
Tests should cover:
1. ✅ Fragment registration and existence
2. ✅ Basic table with header
3. ✅ Table without header (has_header=false)
4. ✅ Column alignment (left, center, right)
5. ✅ Border styles (full, horizontal, minimal, none)
6. ✅ Zebra striping on/off
7. ✅ Table with title
8. ✅ Validation: empty rows
9. ✅ Validation: inconsistent column counts
10. ✅ Validation: invalid alignments
11. ✅ Validation: invalid border style
12. ✅ Compact mode
13. ✅ Width settings (auto, full, percentage)
14. ✅ Group security (cross-group access denied)
15. ✅ Rendering in multiple formats (HTML, Markdown)
16. ✅ Number formatting: currency (USD, EUR, GBP, JPY)
17. ✅ Number formatting: percent
18. ✅ Number formatting: decimal places
19. ✅ Number formatting: integer
20. ✅ Number formatting: accounting (negative as parentheses)
21. ✅ Number formatting: multiple columns
22. ✅ Number formatting: non-numeric values pass through
23. ✅ Validation: invalid column index in number_format
24. ✅ Validation: invalid format specification
25. ✅ Validation: invalid currency code
26. ✅ Theme colors: header_color with theme color name
27. ✅ Theme colors: header_color with custom hex
28. ✅ Theme colors: highlight specific rows
29. ✅ Theme colors: highlight specific columns
30. ✅ Theme colors: stripe_color customization
31. ✅ Theme colors: multiple highlights (rows + columns)
32. ✅ Validation: invalid theme color name
33. ✅ Validation: invalid hex color format
34. ✅ Validation: invalid row index in highlight_rows
35. ✅ Validation: invalid column index in highlight_columns
36. ✅ Rendering: CSS variables for theme colors in HTML output
37. ✅ Sorting: single column ascending
38. ✅ Sorting: single column descending
39. ✅ Sorting: multi-column (primary, secondary)
40. ✅ Sorting: numeric values sorted numerically
41. ✅ Sorting: string values sorted alphabetically (case-insensitive)
42. ✅ Sorting: mixed numeric/string columns
43. ✅ Validation: sort_by column name not in header
44. ✅ Validation: invalid sort order value
45. ✅ Validation: sort_by with has_header=false
46. ✅ Column widths: explicit percentages
47. ✅ Column widths: auto-distribute remaining width
48. ✅ Column widths: HTML rendering with <col> tags
49. ✅ Validation: invalid column width format
50. ✅ Validation: column widths exceed 100%
51. ✅ Integration: sorting + number formatting (sort on raw values)
52. ✅ Integration: sorting + highlighting (indices adjust after sort)

## Open Questions
1. ~~**Number Formatting**: Should we auto-detect and align numbers right?~~
   - **RESOLVED**: Added explicit number_format parameter with currency, percent, decimal, integer, accounting formats
   
2. **Empty Cells**: How to handle empty strings in cells?
   - **Recommendation**: Render as empty cell (no special handling, number formatting skips empty cells). Empty cells sort to end.
   
3. ~~**Column Width**: Should we support per-column width hints?~~
   - **RESOLVED**: Added column_widths parameter with percentage-based widths
   
4. **Max Size**: Should we limit row/column count?
   - **Recommendation**: Yes - max 100 rows, 20 columns (prevent abuse)

5. **Locale for Number Formatting**: Should locale be configurable?
   - **Recommendation**: Default to US locale (en_US) for consistency. Currency symbol determined by format (currency:EUR uses €). Can add locale parameter in future if needed.

6. **Sort Stability**: How to handle equal values during sort?
   - **Recommendation**: Preserve original row order for equal values (stable sort)

7. **Sort + Highlight Interaction**: If rows are sorted, do highlight_rows indices refer to original or sorted order?
   - **Recommendation**: Indices refer to sorted order (what user sees). Document clearly in parameter description.

## Summary
A comprehensive table fragment optimized for financial dashboards and reports with full theme integration:
- Simple array-of-arrays data structure
- **Financial number formatting**: currency, percent, accounting, decimal precision
- **Theme color integration**: Use theme palette colors for headers, highlights, and visual emphasis
- **Flexible highlighting**: Per-row and per-column color highlighting for KPI tables
- **Data sorting**: Single or multi-column sorting by header names (ascending/descending)
- **Column sizing**: Percentage-based column widths with auto-distribution
- Basic visual formatting (alignment, borders, striping)
- Clean rendering across all output formats
- Easy to use via MCP tool
- Locale-aware number formatting (USD, EUR, GBP, JPY, etc.)
- No overly complex features that complicate implementation

**Primary Use Case**: Financial reports, P&L statements, sales dashboards with sorted data, color-coded performance indicators, and properly formatted currency/percentages.

**Key Features**:
- **Sorting**: Sort by revenue descending, then by region ascending
- **Formatting**: Currency in USD, percentages with 2 decimals
- **Colors**: Blue headers, green for positive performance, red for negative
- **Layout**: Fixed column widths (e.g., 25% for amounts, 30% for names)
- **Theme-aware**: All colors use CSS variables that adapt to light/dark themes
