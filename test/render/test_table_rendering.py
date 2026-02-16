"""Tests for table fragment rendering."""

import pytest
from pathlib import Path
from jinja2 import Template


class TestBasicTableRendering:
    """Tests for basic table rendering - Phase 1."""

    @pytest.fixture
    def table_template(self):
        """Load the table template."""
        template_path = Path(
            "data/templates/public/basic_report/fragments/table.html.jinja2"
        )
        with open(template_path, "r") as f:
            return Template(f.read())

    def test_table_with_header(self, table_template):
        """Test table with header row."""
        html = table_template.render(
            rows=[
                ["Name", "Age", "City"],
                ["Alice", "30", "New York"],
                ["Bob", "25", "Boston"],
            ],
            has_header=True,
            title=None,
            width="auto",
        )

        # Verify table structure
        assert 'class="gofr-doc-table"' in html
        assert "<thead>" in html
        assert "<tbody>" in html

        # Verify header row
        assert "Name" in html
        assert "Age" in html
        assert "City" in html

        # Verify data rows
        assert "Alice" in html
        assert "Bob" in html

    def test_table_without_header(self, table_template):
        """Test table without header row."""
        html = table_template.render(
            rows=[["Alice", "30"], ["Bob", "25"]],
            has_header=False,
            title=None,
            width="auto",
        )

        # Verify table structure
        assert 'class="gofr-doc-table"' in html
        assert "<thead>" not in html
        assert "<tbody>" in html
        assert "Alice" in html
        assert "Bob" in html

    def test_table_with_title(self, table_template):
        """Test table with title."""
        html = table_template.render(
            rows=[["Name", "Age"], ["Alice", "30"]],
            has_header=True,
            title="Employee Data",
            width="auto",
        )

        # Verify title
        assert "Employee Data" in html
        assert "table-title" in html

    def test_table_width_auto(self, table_template):
        """Test table with auto width."""
        html = table_template.render(
            rows=[["A", "B"], ["1", "2"]],
            has_header=False,
            title=None,
            width="auto",
        )

        # Auto width should not have inline width style
        assert "width: 100%" not in html

    def test_table_width_full(self, table_template):
        """Test table with full width."""
        html = table_template.render(
            rows=[["A", "B"], ["1", "2"]],
            has_header=False,
            title=None,
            width="full",
        )

        # Full width should have 100% width style
        assert "width: 100%" in html

    def test_table_width_percentage(self, table_template):
        """Test table with percentage width."""
        html = table_template.render(
            rows=[["A", "B"], ["1", "2"]],
            has_header=False,
            title=None,
            width="75%",
        )

        # Should have specific percentage width
        assert "width: 75%" in html

    def test_table_html_structure(self, table_template):
        """Test table HTML structure and classes."""
        html = table_template.render(
            rows=[["Header1", "Header2"], ["Data1", "Data2"]],
            has_header=True,
            title=None,
            width="auto",
        )

        # Verify proper structure
        assert 'class="gofr-doc-table"' in html
        assert "<thead>" in html
        assert "<tbody>" in html
        assert "<th" in html
        assert "<td" in html

    def test_single_row_table(self, table_template):
        """Test table with only header row."""
        html = table_template.render(
            rows=[["Column 1", "Column 2", "Column 3"]],
            has_header=True,
            title=None,
            width="auto",
        )

        # Should have header
        assert "<thead>" in html
        assert "Column 1" in html
        # tbody should exist but be empty
        assert "<tbody>" in html


class TestColumnAlignment:
    """Tests for column alignment - Phase 2."""

    @pytest.fixture
    def table_template(self):
        """Load the table template."""
        template_path = Path(
            "data/templates/public/basic_report/fragments/table.html.jinja2"
        )
        with open(template_path, "r") as f:
            return Template(f.read())

    def test_left_alignment(self, table_template):
        """Test left column alignment."""
        html = table_template.render(
            rows=[["A", "B"], ["1", "2"]],
            has_header=True,
            column_alignments=["left", "left"],
        )

        assert "text-align: left;" in html

    def test_center_alignment(self, table_template):
        """Test center column alignment."""
        html = table_template.render(
            rows=[["A", "B"], ["1", "2"]],
            has_header=True,
            column_alignments=["center", "center"],
        )

        assert "text-align: center;" in html

    def test_right_alignment(self, table_template):
        """Test right column alignment."""
        html = table_template.render(
            rows=[["A", "B"], ["1", "2"]],
            has_header=True,
            column_alignments=["right", "right"],
        )

        assert "text-align: right;" in html

    def test_mixed_alignment(self, table_template):
        """Test mixed column alignments."""
        html = table_template.render(
            rows=[["Name", "Age", "Score"], ["Alice", "30", "95"]],
            has_header=True,
            column_alignments=["left", "center", "right"],
        )

        assert "text-align: left;" in html
        assert "text-align: center;" in html
        assert "text-align: right;" in html


class TestBorderStyles:
    """Tests for border styles - now CSS-driven, inline styles removed."""

    @pytest.fixture
    def table_template(self):
        """Load the table template."""
        template_path = Path(
            "data/templates/public/basic_report/fragments/table.html.jinja2"
        )
        with open(template_path, "r") as f:
            return Template(f.read())

    def test_table_uses_css_class(self, table_template):
        """Test table uses gofr-doc-table class for styling."""
        html = table_template.render(
            rows=[["A", "B"], ["1", "2"]],
            has_header=True,
        )

        # Borders now handled by CSS class, not inline styles
        assert 'class="gofr-doc-table"' in html
        # Should NOT have inline border styles
        assert "border: 1px solid" not in html


class TestZebraStriping:
    """Tests for zebra striping - now CSS-driven via .gofr-doc-table styles."""

    @pytest.fixture
    def table_template(self):
        """Load the table template."""
        template_path = Path(
            "data/templates/public/basic_report/fragments/table.html.jinja2"
        )
        with open(template_path, "r") as f:
            return Template(f.read())

    def test_zebra_striping_removed_from_template(self, table_template):
        """Test zebra striping is now CSS-driven, not in template."""
        html = table_template.render(
            rows=[["A"], ["1"], ["2"], ["3"]],
            has_header=True,
        )

        # Zebra stripe class no longer generated - CSS handles it
        assert "zebra-stripe" not in html
        assert "--gofr-doc-zebra-bg" not in html


class TestCompactMode:
    """Tests for compact mode - now CSS-driven."""

    @pytest.fixture
    def table_template(self):
        """Load the table template."""
        template_path = Path(
            "data/templates/public/basic_report/fragments/table.html.jinja2"
        )
        with open(template_path, "r") as f:
            return Template(f.read())

    def test_compact_mode_adds_class(self, table_template):
        """Test compact mode adds CSS class."""
        html = table_template.render(
            rows=[["A"], ["1"]],
            has_header=True,
            compact=True,
        )

        # Compact mode adds class, CSS handles padding
        assert 'class="gofr-doc-table compact"' in html
        # Should NOT have inline padding
        assert "padding: 4px;" not in html

    def test_normal_mode_no_compact_class(self, table_template):
        """Test normal mode (default) has no compact class."""
        html = table_template.render(
            rows=[["A"], ["1"]],
            has_header=True,
            compact=False,
        )

        assert 'class="gofr-doc-table"' in html
        assert "compact" not in html
        # Should NOT have inline padding
        assert "padding: 8px;" not in html


class TestNumberFormatting:
    """Tests for number formatting - Phase 3."""

    @pytest.fixture
    def table_template(self):
        """Load the table template with format_number filter."""
        from jinja2 import Environment
        from app.formatting.number_formatter import format_number

        template_path = Path(
            "data/templates/public/basic_report/fragments/table.html.jinja2"
        )
        with open(template_path, "r") as f:
            template_source = f.read()

        # Create environment with custom filter
        env = Environment()
        env.filters["format_number"] = format_number
        return env.from_string(template_source)

    def test_currency_formatting(self, table_template):
        """Test currency formatting in table."""
        html = table_template.render(
            rows=[["Product", "Price"], ["Widget", 1234.56]],
            has_header=True,
            number_format={"1": "currency:USD"},
        )

        assert "$1,234.56" in html

    def test_percent_formatting(self, table_template):
        """Test percentage formatting in table."""
        html = table_template.render(
            rows=[["Item", "Discount"], ["Product A", 0.15]],
            has_header=True,
            number_format={"1": "percent"},
        )

        assert "15" in html
        assert "%" in html

    def test_decimal_formatting(self, table_template):
        """Test decimal formatting in table."""
        html = table_template.render(
            rows=[["Item", "Value"], ["Product", 1234.5678]],
            has_header=True,
            number_format={"1": "decimal:2"},
        )

        assert "1,234.57" in html or "1,234.56" in html

    def test_integer_formatting(self, table_template):
        """Test integer formatting in table."""
        html = table_template.render(
            rows=[["Item", "Quantity"], ["Product", 1234.56]],
            has_header=True,
            number_format={"1": "integer"},
        )

        assert "1,235" in html

    def test_accounting_formatting(self, table_template):
        """Test accounting format in table."""
        html = table_template.render(
            rows=[["Item", "Balance"], ["Product A", 100], ["Product B", -50]],
            has_header=True,
            number_format={"1": "accounting"},
        )

        assert "100.00" in html
        assert "(50.00)" in html

    def test_multiple_column_formatting(self, table_template):
        """Test formatting multiple columns."""
        html = table_template.render(
            rows=[
                ["Product", "Price", "Discount", "Qty"],
                ["Widget", 1234.56, 0.10, 5],
            ],
            has_header=True,
            number_format={"1": "currency:USD", "2": "percent", "3": "integer"},
        )

        assert "$1,234.56" in html
        assert "10" in html
        assert "%" in html

    def test_no_formatting(self, table_template):
        """Test table without number formatting."""
        html = table_template.render(
            rows=[["Item", "Value"], ["Product", 1234.56]],
            has_header=True,
            number_format=None,
        )

        # Should display raw value
        assert "1234.56" in html

    def test_formatting_with_text(self, table_template):
        """Test formatting handles non-numeric text."""
        html = table_template.render(
            rows=[["Item", "Value"], ["Product", "N/A"]],
            has_header=True,
            number_format={"1": "currency:USD"},
        )

        # Non-numeric text should pass through
        assert "N/A" in html


class TestColorRendering:
    """Tests for color rendering - now CSS-driven via classes."""

    @pytest.fixture
    def table_template(self):
        """Load the table template with color filters."""
        from app.formatting.number_formatter import format_number
        from app.validation.color_validator import get_css_color
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader("data/templates"),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["format_number"] = format_number
        env.filters["get_css_color"] = get_css_color

        return env.get_template("public/basic_report/fragments/table.html.jinja2")

    def test_highlight_row_adds_class(self, table_template):
        """Test that highlight_rows adds CSS class."""
        html = table_template.render(
            rows=[["Name"], ["Alice"], ["Bob"], ["Charlie"]],
            has_header=False,
            highlight_rows={"1": True},
        )

        assert 'class="highlight"' in html

    def test_highlight_column_adds_class(self, table_template):
        """Test that highlight_columns adds CSS class."""
        html = table_template.render(
            rows=[["Name", "Age", "City"], ["Alice", "30", "NYC"]],
            has_header=False,
            highlight_columns={"1": True},
        )

        assert 'class="highlight-column"' in html

    def test_no_inline_colors(self, table_template):
        """Test that inline color styles are not generated."""
        html = table_template.render(
            rows=[
                ["Product", "Price", "Stock"],
                ["Widget", "10.50", "100"],
                ["Gadget", "25.00", "50"],
            ],
            has_header=True,
            highlight_rows={"2": True},
            highlight_columns={"1": True},
        )

        # No inline background colors
        assert "background-color:" not in html
        # But classes should be present
        assert "gofr-doc-table" in html


class TestSorting:
    """Tests for table sorting - Phase 5."""

    @pytest.fixture
    def table_template(self):
        """Load the table template with all filters."""
        from app.formatting.number_formatter import format_number
        from app.validation.color_validator import get_css_color
        from app.formatting.table_sorter import sort_table_rows
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader("data/templates"),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["format_number"] = format_number
        env.filters["get_css_color"] = get_css_color
        env.filters["sort_table"] = sort_table_rows

        return env.get_template("public/basic_report/fragments/table.html.jinja2")

    def test_sort_by_column_name_ascending(self):
        """Test sorting by column name in ascending order."""
        from app.formatting.number_formatter import format_number
        from app.validation.color_validator import get_css_color
        from app.formatting.table_sorter import sort_table_rows
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader("data/templates"),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["format_number"] = format_number
        env.filters["get_css_color"] = get_css_color
        env.filters["sort_table"] = sort_table_rows
        template = env.get_template("public/basic_report/fragments/table.html.jinja2")

        html = template.render(
            rows=[
                ["Name", "Age"],
                ["Charlie", "25"],
                ["Alice", "30"],
                ["Bob", "35"],
            ],
            has_header=True,
            sort_by="Name",
        )

        # Verify Alice appears before Bob, Bob before Charlie
        alice_pos = html.find("Alice")
        bob_pos = html.find("Bob")
        charlie_pos = html.find("Charlie")

        assert alice_pos < bob_pos < charlie_pos

    def test_sort_by_numeric_column(self):
        """Test sorting numeric column."""
        from app.formatting.number_formatter import format_number
        from app.validation.color_validator import get_css_color
        from app.formatting.table_sorter import sort_table_rows
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader("data/templates"),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["format_number"] = format_number
        env.filters["get_css_color"] = get_css_color
        env.filters["sort_table"] = sort_table_rows
        template = env.get_template("public/basic_report/fragments/table.html.jinja2")

        html = template.render(
            rows=[
                ["Name", "Age"],
                ["Charlie", "100"],
                ["Alice", "25"],
                ["Bob", "50"],
            ],
            has_header=True,
            sort_by="Age",
        )

        # Verify sorted by numeric value: 25, 50, 100
        # Check that Alice (25) appears before Bob (50) who appears before Charlie (100)
        alice_pos = html.find("Alice")
        bob_pos = html.find("Bob")
        charlie_pos = html.find("Charlie")

        assert alice_pos < bob_pos < charlie_pos

    def test_sort_with_number_formatting(self):
        """Test that sorting happens before number formatting."""
        from app.formatting.number_formatter import format_number
        from app.validation.color_validator import get_css_color
        from app.formatting.table_sorter import sort_table_rows
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader("data/templates"),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["format_number"] = format_number
        env.filters["get_css_color"] = get_css_color
        env.filters["sort_table"] = sort_table_rows
        template = env.get_template("public/basic_report/fragments/table.html.jinja2")

        html = template.render(
            rows=[
                ["Product", "Price"],
                ["Widget", "100.50"],
                ["Gadget", "25.00"],
                ["Doohickey", "50.25"],
            ],
            has_header=True,
            sort_by="Price",
            number_format={"1": "currency:USD"},
        )

        # Prices should be sorted: 25, 50.25, 100.50
        # But displayed as: $25.00, $50.25, $100.50
        price_25_pos = html.find("$25.00")
        price_50_pos = html.find("$50.25")
        price_100_pos = html.find("$100.50")

        assert price_25_pos < price_50_pos < price_100_pos

    def test_sort_descending(self):
        """Test sorting in descending order."""
        from app.formatting.number_formatter import format_number
        from app.validation.color_validator import get_css_color
        from app.formatting.table_sorter import sort_table_rows
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader("data/templates"),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["format_number"] = format_number
        env.filters["get_css_color"] = get_css_color
        env.filters["sort_table"] = sort_table_rows
        template = env.get_template("public/basic_report/fragments/table.html.jinja2")

        html = template.render(
            rows=[
                ["Name", "Score"],
                ["Alice", "50"],
                ["Bob", "100"],
                ["Charlie", "75"],
            ],
            has_header=True,
            sort_by={"column": "Score", "order": "desc"},
        )

        # Verify descending: 100, 75, 50
        # Bob (100) should appear before Charlie (75) who appears before Alice (50)
        bob_pos = html.find("Bob")
        charlie_pos = html.find("Charlie")
        alice_pos = html.find("Alice")

        assert bob_pos < charlie_pos < alice_pos

    def test_multi_column_sort(self):
        """Test multi-column sorting."""
        from app.formatting.number_formatter import format_number
        from app.validation.color_validator import get_css_color
        from app.formatting.table_sorter import sort_table_rows
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader("data/templates"),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        env.filters["format_number"] = format_number
        env.filters["get_css_color"] = get_css_color
        env.filters["sort_table"] = sort_table_rows
        template = env.get_template("public/basic_report/fragments/table.html.jinja2")

        html = template.render(
            rows=[
                ["Dept", "Name", "Age"],
                ["Sales", "Bob", "30"],
                ["Eng", "Alice", "25"],
                ["Sales", "Alice", "28"],
                ["Eng", "Bob", "35"],
            ],
            has_header=True,
            sort_by=["Dept", "Name"],
        )

        # Should sort: Eng/Alice, Eng/Bob, Sales/Alice, Sales/Bob
        # Verify order by checking text positions
        # First Eng row should appear before first Sales row
        eng_pos = html.find("Eng")
        sales_pos = html.find("Sales")

        assert eng_pos < sales_pos
        assert eng_pos > 0  # Make sure it was found


class TestColumnWidthsRendering:
    """Tests for column widths rendering - Phase 6."""

    @pytest.fixture
    def table_template(self):
        """Load the table template."""
        template_path = Path(
            "data/templates/public/basic_report/fragments/table.html.jinja2"
        )
        with open(template_path, "r") as f:
            return Template(f.read())

    def test_column_widths_full_specification(self, table_template):
        """Test table with all column widths specified."""
        html = table_template.render(
            rows=[["Name", "Age", "City"], ["Alice", "30", "NYC"]],
            has_header=True,
            column_widths={"0": "40%", "1": "20%", "2": "40%"},
        )

        assert "<colgroup>" in html
        assert '<col style="width: 40%;">' in html
        assert '<col style="width: 20%;">' in html

    def test_column_widths_partial_specification(self, table_template):
        """Test table with partial column widths (auto-distribute remaining)."""
        html = table_template.render(
            rows=[["A", "B", "C"], ["1", "2", "3"]],
            has_header=False,
            column_widths={"0": "30%", "2": "30%"},
        )

        assert "<colgroup>" in html
        # Check that columns 0 and 2 have widths
        lines = html.split("\n")
        col_lines = [
            line
            for line in lines
            if "<col" in line and "</col" not in line and "<colgroup>" not in line
        ]
        assert len(col_lines) == 3
        assert 'style="width: 30%;"' in col_lines[0]
        assert 'style="width:' not in col_lines[1]  # Column 1 has no width
        assert 'style="width: 30%;"' in col_lines[2]

    def test_no_column_widths(self, table_template):
        """Test table without column widths (no colgroup)."""
        html = table_template.render(rows=[["A", "B"], ["1", "2"]], has_header=False)

        assert "<colgroup>" not in html


class TestMarkdownTableRendering:
    """Tests for markdown table rendering - Phase 8."""

    @pytest.fixture
    def rendering_engine(self):
        """Create rendering engine for markdown conversion."""
        from app.rendering.engine import RenderingEngine
        from app.logger import ConsoleLogger
        from unittest.mock import Mock

        logger = ConsoleLogger()

        # Mock registries (not needed for _html_to_markdown tests)
        mock_template_registry = Mock()
        mock_style_registry = Mock()

        return RenderingEngine(
            template_registry=mock_template_registry,
            style_registry=mock_style_registry,
            logger=logger,
        )

    @pytest.mark.asyncio
    async def test_basic_table_structure_in_markdown(self, rendering_engine):
        """Test that HTML tables convert to proper markdown table structure."""
        html = """
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Age</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Alice</td>
                    <td>30</td>
                </tr>
            </tbody>
        </table>
        """

        markdown = await rendering_engine._html_to_markdown(html)

        # Check table structure
        assert "|" in markdown
        assert "Name" in markdown
        assert "Age" in markdown
        assert "Alice" in markdown
        assert "30" in markdown
        # Check separator exists
        assert "---" in markdown or "---|" in markdown

    @pytest.mark.asyncio
    async def test_alignment_markers_left(self, rendering_engine):
        """Test left alignment markers in markdown tables."""
        from app.validation.document_models import DocumentSession

        html = """
        <table>
            <thead><tr><th>Name</th><th>City</th></tr></thead>
            <tbody><tr><td>Alice</td><td>NYC</td></tr></tbody>
        </table>
        """

        session = DocumentSession(
            session_id="test",
            template_id="basic_report",
            group="public",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            fragments=[  # type: ignore[arg-type] - test uses simplified dict format
                {
                    "fragment_id": "table1",
                    "parameters": {
                        "rows": [["Name", "City"], ["Alice", "NYC"]],
                        "column_alignments": ["left", "left"],
                    },
                }
            ],
        )

        markdown = await rendering_engine._html_to_markdown(html, session)

        # Check for left alignment markers
        assert ":---" in markdown
        # Should have two left alignments
        lines = markdown.split("\n")
        sep_line = [line for line in lines if ":---" in line][0]
        assert sep_line.count(":---") >= 2

    @pytest.mark.asyncio
    async def test_alignment_markers_mixed(self, rendering_engine):
        """Test mixed alignment markers (left, center, right)."""
        from app.validation.document_models import DocumentSession

        html = """
        <table>
            <thead><tr><th>Name</th><th>Age</th><th>City</th></tr></thead>
            <tbody><tr><td>Alice</td><td>30</td><td>NYC</td></tr></tbody>
        </table>
        """

        session = DocumentSession(
            session_id="test",
            template_id="basic_report",
            group="public",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            fragments=[  # type: ignore[arg-type] - test uses simplified dict format
                {
                    "fragment_id": "table1",
                    "parameters": {
                        "rows": [["Name", "Age", "City"], ["Alice", "30", "NYC"]],
                        "column_alignments": ["left", "right", "center"],
                    },
                }
            ],
        )

        markdown = await rendering_engine._html_to_markdown(html, session)

        # Check for specific alignment markers
        lines = markdown.split("\n")
        sep_line = [line for line in lines if ":---" in line or "---:" in line][0]

        assert ":---" in sep_line  # Left alignment
        assert "---:" in sep_line  # Right alignment
        assert ":---:" in sep_line  # Center alignment

    @pytest.mark.asyncio
    async def test_number_formatting_preserved_in_markdown(self, rendering_engine):
        """Test that number formatting is preserved in markdown cells."""
        from app.validation.document_models import DocumentSession

        html = """
        <table>
            <thead><tr><th>Item</th><th>Price</th></tr></thead>
            <tbody>
                <tr><td>Widget</td><td>$1,234.56</td></tr>
                <tr><td>Gadget</td><td>$89.00</td></tr>
            </tbody>
        </table>
        """

        session = DocumentSession(
            session_id="test",
            template_id="basic_report",
            group="public",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            fragments=[  # type: ignore[arg-type] - test uses simplified dict format
                {
                    "fragment_id": "table1",
                    "parameters": {
                        "rows": [
                            ["Item", "Price"],
                            ["Widget", "$1,234.56"],
                            ["Gadget", "$89.00"],
                        ],
                        "number_format": {"1": "currency:USD"},
                    },
                }
            ],
        )

        markdown = await rendering_engine._html_to_markdown(html, session)

        # Check formatted numbers are in markdown
        assert "$1,234.56" in markdown
        assert "$89.00" in markdown
        assert "Widget" in markdown
        assert "Gadget" in markdown

    @pytest.mark.asyncio
    async def test_title_rendered_in_markdown(self, rendering_engine):
        """Test that table title is rendered in markdown."""
        html = """
        <div class="table-title">Financial Summary</div>
        <table>
            <thead><tr><th>Category</th><th>Amount</th></tr></thead>
            <tbody><tr><td>Revenue</td><td>$10,000</td></tr></tbody>
        </table>
        """

        markdown = await rendering_engine._html_to_markdown(html)

        # Title should appear in markdown
        assert "Financial Summary" in markdown

    @pytest.mark.asyncio
    async def test_colors_not_in_markdown(self, rendering_engine):
        """Test that HTML colors/styling are omitted from markdown (expected limitation)."""
        from app.validation.document_models import DocumentSession

        html = """
        <table>
            <thead>
                <tr style="background-color: blue;">
                    <th>Name</th>
                </tr>
            </thead>
            <tbody>
                <tr style="background-color: yellow;">
                    <td>Alice</td>
                </tr>
            </tbody>
        </table>
        """

        session = DocumentSession(
            session_id="test",
            template_id="basic_report",
            group="public",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            fragments=[  # type: ignore[arg-type] - test uses simplified dict format
                {
                    "fragment_id": "table1",
                    "parameters": {
                        "rows": [["Name"], ["Alice"]],
                        "header_color": "primary",
                        "stripe_color": "light",
                    },
                }
            ],
        )

        markdown = await rendering_engine._html_to_markdown(html, session)

        # Colors/styles should not appear in markdown
        assert "background-color" not in markdown
        assert "blue" not in markdown.lower() or "Alice" in markdown  # Text preserved
        assert "style=" not in markdown

        # But content should be there
        assert "Name" in markdown
        assert "Alice" in markdown

    @pytest.mark.asyncio
    async def test_multiple_tables_with_different_alignments(self, rendering_engine):
        """Test document with multiple tables, each with different alignments."""
        from app.validation.document_models import DocumentSession

        html = """
        <table>
            <thead><tr><th>A</th><th>B</th></tr></thead>
            <tbody><tr><td>1</td><td>2</td></tr></tbody>
        </table>
        <table>
            <thead><tr><th>X</th><th>Y</th><th>Z</th></tr></thead>
            <tbody><tr><td>10</td><td>20</td><td>30</td></tr></tbody>
        </table>
        """

        session = DocumentSession(
            session_id="test",
            template_id="basic_report",
            group="public",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            fragments=[  # type: ignore[arg-type] - test uses simplified dict format
                {
                    "fragment_id": "table1",
                    "parameters": {
                        "rows": [["A", "B"], ["1", "2"]],
                        "column_alignments": ["left", "right"],
                    },
                },
                {
                    "fragment_id": "table2",
                    "parameters": {
                        "rows": [["X", "Y", "Z"], ["10", "20", "30"]],
                        "column_alignments": ["center", "center", "center"],
                    },
                },
            ],
        )

        markdown = await rendering_engine._html_to_markdown(html, session)

        # Find all separator lines
        lines = markdown.split("\n")
        sep_lines = [line for line in lines if ":---" in line or "---:" in line]

        # Should have 2 tables
        assert len(sep_lines) >= 2

        # First table: left, right
        assert ":---" in sep_lines[0]  # Left
        assert "---:" in sep_lines[0]  # Right

        # Second table: center, center, center
        assert ":---:" in sep_lines[1]  # Center
        assert sep_lines[1].count(":---:") >= 3
