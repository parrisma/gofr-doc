# Table Fragment Implementation Plan

## Overview
Phased implementation of the table fragment feature with number formatting, theme colors, sorting, and column widths. Each phase includes implementation + tests, with all tests passing before moving to next phase.

## Dependencies
- **New**: Babel>=2.13.0 (for number/currency formatting)
- **Existing**: Jinja2, WeasyPrint, html2text, PyYAML, pytest

## Phase 1: Foundation - Basic Table Structure
**Goal**: Get basic table rendering working with validation

### 1.1 Add Babel Dependency
- [ ] Update `requirements.txt` with `Babel>=2.13.0`
- [ ] Install: `pip install Babel>=2.13.0`
- [ ] Verify: `python -c "from babel.numbers import format_currency; print('OK')"`

### 1.2 Create Validation Models
**File**: `app/validation/table_validator.py`
- [ ] Create `TableData` model (Pydantic)
- [ ] Validate rows structure (non-empty, array of arrays)
- [ ] Validate consistent column counts
- [ ] Basic parameter validation (has_header, title, width)

**Tests**: `test/validation/test_table_validator.py`
- [ ] Test valid table data
- [ ] Test empty rows error
- [ ] Test inconsistent columns error
- [ ] Test parameter validation
- [ ] Run tests: `pytest test/validation/test_table_validator.py -v`

### 1.3 Create Basic Template
**File**: `test/render/data/docs/templates/public/basic_report/fragments/table.html.jinja2`
- [ ] Basic HTML table structure (`<table>`, `<thead>`, `<tbody>`)
- [ ] Render rows with header detection
- [ ] Optional title rendering
- [ ] Basic CSS classes (`.doco-table`)

**File**: `test/render/data/docs/templates/public/basic_report/template.yaml`
- [ ] Add `table` fragment definition
- [ ] Define parameters: rows, has_header, title, width

**Tests**: `test/render/test_table_rendering.py`
- [ ] Test table with header
- [ ] Test table without header
- [ ] Test table with title
- [ ] Test HTML output structure
- [ ] Run tests: `pytest test/render/test_table_rendering.py -v`

### 1.4 Integration Test
- [ ] Run full test suite: `./scripts/run_tests.sh --with-servers`
- [ ] Verify: All 307 tests still pass

**Deliverable**: Basic table rendering works, all tests pass

---

## Phase 2: Alignment and Visual Styling
**Goal**: Add column alignment, borders, zebra striping

### 2.1 Extend Validator
**File**: `app/validation/table_validator.py`
- [ ] Add column_alignments validation (left/center/right)
- [ ] Add border_style validation (full/horizontal/minimal/none)
- [ ] Add zebra_stripe, compact parameters

**Tests**: `test/validation/test_table_validator.py`
- [ ] Test valid alignments
- [ ] Test invalid alignment values
- [ ] Test alignment count mismatch
- [ ] Test border style validation
- [ ] Run tests: `pytest test/validation/test_table_validator.py -v`

### 2.2 Update Template with Styling
**File**: `test/render/data/docs/templates/public/basic_report/fragments/table.html.jinja2`
- [ ] Add alignment styles (inline or CSS classes)
- [ ] Add border styles (conditional CSS classes)
- [ ] Add zebra striping (odd/even row classes)
- [ ] Add compact mode (reduced padding)
- [ ] Add width handling (auto/full/percentage)

**File**: `test/render/data/docs/templates/public/basic_report/template.yaml`
- [ ] Update schema with alignment, border, styling parameters

**Tests**: `test/render/test_table_rendering.py`
- [ ] Test left/center/right alignment
- [ ] Test all border styles
- [ ] Test zebra striping on/off
- [ ] Test compact mode
- [ ] Test width settings
- [ ] Run tests: `pytest test/render/test_table_rendering.py -v`

### 2.3 Integration Test
- [ ] Run full test suite: `./scripts/run_tests.sh --with-servers`
- [ ] Verify: All tests pass

**Deliverable**: Tables render with full visual styling options

---

## Phase 3: Number Formatting
**Goal**: Add financial number formatting with Babel

### 3.1 Create Number Formatter Module
**File**: `app/formatting/__init__.py`
- [ ] Create formatting package

**File**: `app/formatting/number_formatter.py`
- [ ] Implement `format_number(value, format_spec)` function
- [ ] Support `currency:CODE` (USD, EUR, GBP, JPY, etc.)
- [ ] Support `percent`
- [ ] Support `decimal:N`
- [ ] Support `integer`
- [ ] Support `accounting` (negative as parentheses)
- [ ] Handle non-numeric values (pass through)
- [ ] Handle empty cells (return empty)

**Tests**: `test/formatting/__init__.py` (create directory)
**Tests**: `test/formatting/test_number_formatter.py`
- [ ] Test currency formatting (USD, EUR, GBP, JPY)
- [ ] Test percent formatting
- [ ] Test decimal formatting (various precisions)
- [ ] Test integer formatting
- [ ] Test accounting format (negatives)
- [ ] Test non-numeric pass-through
- [ ] Test empty cell handling
- [ ] Run tests: `pytest test/formatting/test_number_formatter.py -v`

### 3.2 Extend Table Validator
**File**: `app/validation/table_validator.py`
- [ ] Add number_format validation
- [ ] Validate column indices (0-based integers)
- [ ] Validate format specifications
- [ ] Validate currency codes (ISO 4217)

**Tests**: `test/validation/test_table_validator.py`
- [ ] Test valid number_format
- [ ] Test invalid column index
- [ ] Test invalid format spec
- [ ] Test invalid currency code
- [ ] Run tests: `pytest test/validation/test_table_validator.py -v`

### 3.3 Integrate Formatter into Template
**File**: `test/render/data/docs/templates/public/basic_report/fragments/table.html.jinja2`
- [ ] Add Jinja2 custom filter for number formatting
- [ ] Apply formatting per column during render
- [ ] Preserve raw values in data structure

**File**: `app/rendering/engine.py` (if needed)
- [ ] Register custom Jinja2 filter for number formatting

**Tests**: `test/render/test_table_rendering.py`
- [ ] Test currency formatting in rendered table
- [ ] Test percent formatting in rendered table
- [ ] Test decimal formatting in rendered table
- [ ] Test accounting format in rendered table
- [ ] Test multiple columns with different formats
- [ ] Run tests: `pytest test/render/test_table_rendering.py -v`

### 3.4 Integration Test
- [ ] Run full test suite: `./scripts/run_tests.sh --with-servers`
- [ ] Verify: All tests pass

**Deliverable**: Financial data rendered with proper formatting

---

## Phase 4: Theme Color Integration
**Goal**: Add theme color support for headers and highlights

### 4.1 Create Color Validator
**File**: `app/validation/color_validator.py`
- [ ] Validate theme color names (blue, orange, green, red, purple, brown, pink, gray)
- [ ] Validate hex color format (#RRGGBB)
- [ ] Create `validate_color(value)` function

**Tests**: `test/validation/test_color_validator.py`
- [ ] Test valid theme colors
- [ ] Test valid hex colors
- [ ] Test invalid color names
- [ ] Test invalid hex format
- [ ] Run tests: `pytest test/validation/test_color_validator.py -v`

### 4.2 Extend Table Validator with Colors
**File**: `app/validation/table_validator.py`
- [ ] Add header_color validation
- [ ] Add stripe_color validation
- [ ] Add highlight_rows validation (indices + colors)
- [ ] Add highlight_columns validation (indices + colors)

**Tests**: `test/validation/test_table_validator.py`
- [ ] Test valid header_color
- [ ] Test valid highlight_rows
- [ ] Test valid highlight_columns
- [ ] Test invalid row/column indices
- [ ] Test invalid colors
- [ ] Run tests: `pytest test/validation/test_table_validator.py -v`

### 4.3 Update Template with Color Support
**File**: `test/render/data/docs/templates/public/basic_report/fragments/table.html.jinja2`
- [ ] Map theme color names to CSS variables
- [ ] Apply header_color to header row
- [ ] Apply highlight_rows with semi-transparent overlays
- [ ] Apply highlight_columns with semi-transparent overlays
- [ ] Support custom hex colors

**Tests**: `test/render/test_table_rendering.py`
- [ ] Test header with theme color
- [ ] Test header with hex color
- [ ] Test row highlighting
- [ ] Test column highlighting
- [ ] Test CSS variable usage in HTML
- [ ] Run tests: `pytest test/render/test_table_rendering.py -v`

### 4.4 Integration Test
- [ ] Run full test suite: `./scripts/run_tests.sh --with-servers`
- [ ] Verify: All tests pass

**Deliverable**: Tables render with theme-aware colors

---

## Phase 5: Sorting
**Goal**: Add single and multi-column sorting

### 5.1 Create Table Sorter Module
**File**: `app/formatting/table_sorter.py`
- [ ] Implement `sort_table_rows(rows, sort_by, header_row)` function
- [ ] Parse sort_by parameter (strings or objects)
- [ ] Support single column sort (ascending/descending)
- [ ] Support multi-column sort
- [ ] Auto-detect numeric vs string columns
- [ ] Case-insensitive string sorting
- [ ] Stable sort (preserve order for equal values)

**Tests**: `test/formatting/test_table_sorter.py`
- [ ] Test single column ascending
- [ ] Test single column descending
- [ ] Test multi-column sort
- [ ] Test numeric sorting
- [ ] Test string sorting (case-insensitive)
- [ ] Test mixed numeric/string columns
- [ ] Test stable sort
- [ ] Run tests: `pytest test/formatting/test_table_sorter.py -v`

### 5.2 Extend Table Validator with Sorting
**File**: `app/validation/table_validator.py`
- [ ] Add sort_by validation
- [ ] Validate column names exist in header
- [ ] Validate sort order (asc/desc)
- [ ] Validate sort requires header

**Tests**: `test/validation/test_table_validator.py`
- [ ] Test valid sort_by
- [ ] Test invalid column name
- [ ] Test invalid sort order
- [ ] Test sort without header
- [ ] Run tests: `pytest test/validation/test_table_validator.py -v`

### 5.3 Integrate Sorting into Rendering
**File**: `app/rendering/engine.py` or template preprocessing
- [ ] Apply sorting before rendering
- [ ] Sort on raw values (before number formatting)
- [ ] Preserve header row position

**Tests**: `test/render/test_table_rendering.py`
- [ ] Test sorted table rendering
- [ ] Test sort with number formatting (verify raw sort)
- [ ] Test multi-column sort in output
- [ ] Run tests: `pytest test/render/test_table_rendering.py -v`

### 5.4 Integration Test
- [ ] Run full test suite: `./scripts/run_tests.sh --with-servers`
- [ ] Verify: All tests pass

**Deliverable**: Tables can be sorted by column headers

---

## Phase 6: Column Widths
**Goal**: Add percentage-based column width control

### 6.1 Create Width Validator
**File**: `app/validation/table_validator.py`
- [ ] Add column_widths validation
- [ ] Validate column indices
- [ ] Validate percentage format ("N%")
- [ ] Validate total doesn't exceed 100%
- [ ] Calculate auto-distributed widths

**Tests**: `test/validation/test_table_validator.py`
- [ ] Test valid column_widths
- [ ] Test invalid column index
- [ ] Test invalid percentage format
- [ ] Test widths exceeding 100%
- [ ] Test auto-distribution calculation
- [ ] Run tests: `pytest test/validation/test_table_validator.py -v`

### 6.2 Update Template with Width Support
**File**: `test/render/data/docs/templates/public/basic_report/fragments/table.html.jinja2`
- [ ] Add `<colgroup>` with `<col>` elements
- [ ] Apply width percentages to columns
- [ ] Auto-distribute remaining width

**Tests**: `test/render/test_table_rendering.py`
- [ ] Test explicit column widths
- [ ] Test auto-distribution
- [ ] Test HTML structure with <col> tags
- [ ] Run tests: `pytest test/render/test_table_rendering.py -v`

### 6.3 Integration Test
- [ ] Run full test suite: `./scripts/run_tests.sh --with-servers`
- [ ] Verify: All tests pass

**Deliverable**: Tables render with precise column widths

---

## Phase 7: MCP Tool Integration
**Goal**: Add table fragment as MCP tool (not separate like image)

### 7.1 Update Template Schema
**File**: `test/render/data/docs/templates/public/basic_report/template.yaml`
- [ ] Add complete table fragment definition
- [ ] Document all parameters with types
- [ ] Add examples in description

### 7.2 MCP Tool Testing
**Tests**: `test/mcp/test_table_fragment.py`
- [ ] Test add_fragment with table
- [ ] Test all parameter combinations
- [ ] Test validation errors
- [ ] Test group security
- [ ] Test rendering in document
- [ ] Run tests: `pytest test/mcp/test_table_fragment.py -v`

### 7.3 Integration Test
- [ ] Run full test suite: `./scripts/run_tests.sh --with-servers`
- [ ] Verify: All tests pass (307 + new table tests)

**Deliverable**: Table fragment available via MCP tool

---

## Phase 8: Markdown Output Support
**Goal**: Render tables in Markdown format

### 8.1 Create Markdown Template (Optional)
**File**: `test/render/data/docs/templates/public/basic_report/fragments/table.md.jinja2`
- [ ] Standard Markdown table syntax
- [ ] Column alignment markers (`:---`, `:---:`, `---:`)
- [ ] Number formatting preserved
- [ ] Note: Colors/highlighting not supported in Markdown

**Tests**: `test/render/test_table_rendering.py`
- [ ] Test Markdown output generation
- [ ] Test alignment in Markdown
- [ ] Test formatted numbers in Markdown
- [ ] Run tests: `pytest test/render/test_table_rendering.py -v`

### 8.2 Integration Test
- [ ] Run full test suite: `./scripts/run_tests.sh --with-servers`
- [ ] Verify: All tests pass

**Deliverable**: Tables render in both HTML and Markdown

---

## Phase 9: End-to-End Integration Tests
**Goal**: Comprehensive workflow testing

### 9.1 Create Workflow Tests
**Tests**: `test/workflow/test_financial_table_workflow.py`
- [ ] Test complete financial report workflow
- [ ] Create session → add table with all features → render
- [ ] Test multiple tables in one document
- [ ] Test table + image fragments together
- [ ] Test different output formats (HTML, PDF, Markdown)
- [ ] Run tests: `pytest test/workflow/test_financial_table_workflow.py -v`

### 9.2 Performance Testing
- [ ] Test table with max rows (100 rows)
- [ ] Test table with max columns (20 columns)
- [ ] Test sorting performance
- [ ] Test rendering performance

### 9.3 Final Integration Test
- [ ] Run full test suite: `./scripts/run_tests.sh --with-servers`
- [ ] Verify: All tests pass
- [ ] Verify: No performance regressions

**Deliverable**: Production-ready table fragment

---

## Phase 10: Documentation and Cleanup
**Goal**: Polish and document

### 10.1 Update Documentation
- [ ] Add table fragment examples to docs
- [ ] Update README if needed
- [ ] Document Babel dependency

### 10.2 Code Review Checklist
- [ ] All error codes documented
- [ ] All validation clear and tested
- [ ] All edge cases handled
- [ ] Code follows project patterns
- [ ] No TODOs or FIXMEs left

### 10.3 Final Verification
- [ ] Run full test suite: `./scripts/run_tests.sh --with-servers`
- [ ] Review test coverage
- [ ] Verify all 52 test cases from design doc covered

**Deliverable**: Complete, documented, tested table fragment feature

---

## Rollback Strategy
If any phase fails:
1. **Git**: Commit after each successful phase
2. **Tests**: All tests must pass before proceeding
3. **Rollback**: `git reset --hard <last-good-commit>`
4. **Debug**: Fix issues in isolation before re-attempting phase

## Success Criteria
- [ ] All existing tests pass (307 tests)
- [ ] All new table tests pass (52+ tests)
- [ ] No performance regressions
- [ ] Code follows existing patterns
- [ ] Documentation complete
- [ ] Example usage demonstrated

## Estimated Timeline
- Phase 1: 2-3 hours
- Phase 2: 1-2 hours
- Phase 3: 3-4 hours
- Phase 4: 2-3 hours
- Phase 5: 3-4 hours
- Phase 6: 1-2 hours
- Phase 7: 1-2 hours
- Phase 8: 1-2 hours
- Phase 9: 2-3 hours
- Phase 10: 1 hour

**Total**: ~18-26 hours (2-3 days of focused work)

## Phase Execution Command
For each phase:
```bash
# 1. Implement features
# 2. Add tests
# 3. Run phase tests
pytest test/<specific-test-file> -v
# 4. Run full suite
./scripts/run_tests.sh --with-servers
# 5. Commit if all pass
git add .
git commit -m "Phase N: <description>"
```
