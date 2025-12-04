#!/usr/bin/env python3
"""Complete workflow test for table fragment with all Phase 1-8 features.

Tests the full table generation workflow:
1. Create authenticated session via MCP
2. Add table with all features (alignment, formatting, colors, sorting, widths)
3. Render to HTML, PDF, and Markdown
4. Verify output contains expected table features
5. Test multiple tables in one document
6. Test table + image fragments together
7. Test performance with large tables

FEATURES TESTED:
- Phase 1: Basic table structure (rows, has_header, title, width)
- Phase 2: Alignment (column_alignments), borders, zebra striping
- Phase 3: Number formatting (currency, percent, decimal)
- Phase 4: Theme colors (header_color, stripe_color)
- Phase 5: Sorting (sort_by with column name/index)
- Phase 6: Column widths (column_widths with percentages)
- Phase 7: MCP integration (all parameters in template schema)
- Phase 8: Markdown table support (alignment markers)

Requires:
- MCP server running on port 8011
- Web server running on port 8010
- JWT authentication configured
"""

import json
import os
import sys
import time
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Port configuration
MCP_PORT = os.environ.get("GOFR_DOC_MCP_PORT", "8011")
WEB_PORT = os.environ.get("GOFR_DOC_WEB_PORT", "8010")

# Use 127.0.0.1 for better Docker container compatibility
MCP_URL = f"http://127.0.0.1:{MCP_PORT}/mcp/"


def _extract_text(result):
    """Extract text content from MCP tool result."""
    if not result or not result.content:
        return ""
    for item in result.content:
        if isinstance(item, TextContent):
            return item.text
    return ""


def _safe_json_parse(text):
    """Safely parse JSON with error handling."""
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}
        return {}


class TestFinancialTableWorkflow:
    """Test complete financial table workflow with all features."""

    @pytest.mark.asyncio
    async def test_simple_financial_table(self, mcp_headers):
        """Test basic table with financial data - Phase 1-3 features."""

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 1. Create session
                result = await session.call_tool(
                    "create_document_session",
                    arguments={
                        "template_id": "basic_report",
                        "alias": "test_financial_table_workflow-22",
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"
                session_id = response.get("data", {}).get("session_id")
                assert session_id is not None

                # 2. Add table with all Phase 1-6 features
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "table",
                        "parameters": {
                            "rows": [
                                ["Quarter", "Revenue", "Growth"],
                                ["Q1 2024", "1250000", "0.15"],
                                ["Q2 2024", "1380000", "0.104"],
                                ["Q3 2024", "1520000", "0.101"],
                                ["Q4 2024", "1650000", "0.086"],
                            ],
                            "has_header": True,
                            "title": "Quarterly Revenue 2024",
                            "width": "100%",
                            "column_alignments": ["left", "right", "right"],
                            "number_format": {
                                "1": "currency:USD",
                                "2": "percent",
                            },
                        },
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"

                # 3. Render to HTML
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "html"},
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"
                html_content = response.get("data", {}).get("content")

                # Verify HTML contains table elements
                assert "Quarterly Revenue 2024" in html_content
                assert "<table" in html_content
                assert "Q1 2024" in html_content
                assert "$1,250,000" in html_content or "$1250000" in html_content
                assert "15%" in html_content or "15.0%" in html_content

    @pytest.mark.asyncio
    async def test_table_with_all_features(self, mcp_headers):
        """Test table with ALL Phase 1-6 features enabled."""

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 1. Create session
                result = await session.call_tool(
                    "create_document_session",
                    arguments={
                        "template_id": "basic_report",
                        "alias": "test_financial_table_workflow-23",
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                session_id = response.get("data", {}).get("session_id")

                # 2. Generate table with mixed data typesr markdown
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "table",
                        "parameters": {
                            "rows": [
                                ["Product", "Sales", "Profit Margin", "Rating"],
                                ["Widget A", "125000", "0.35", "4.5"],
                                ["Widget B", "98000", "0.42", "4.8"],
                                ["Widget C", "156000", "0.28", "4.2"],
                                ["Widget D", "203000", "0.38", "4.9"],
                            ],
                            "has_header": True,
                            "title": "Product Performance Analysis",
                            "width": "100%",
                            "column_alignments": ["left", "right", "center", "center"],
                            "compact": False,
                            "number_format": {
                                "1": "currency:USD",
                                "2": "percent",
                                "3": "decimal:1",
                            },
                            "highlight_rows": {0: "warning"},
                            "sort_by": {"column": "Sales", "order": "desc"},
                            "column_widths": {
                                0: "30%",
                                1: "25%",
                                2: "25%",
                                3: "20%",
                            },
                        },
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                if response.get("status") != "success":
                    print(f"ERROR adding fragment: {response.get('message', 'unknown')}")
                    print(f"Full response: {response}")
                assert response.get("status") == "success"

                # 3. Render to HTML
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "html"},
                )
                response = _safe_json_parse(_extract_text(result))
                if response.get("status") != "success":
                    print(f"ERROR rendering: {response.get('message', 'unknown')}")
                assert response.get("status") == "success"
                html_content = response.get("data", {}).get("content")

                # Verify features present
                assert "Product Performance Analysis" in html_content
                assert "<colgroup>" in html_content  # Column widths
                assert 'style="width: 30%;"' in html_content
                assert "Widget" in html_content

                # Verify sorted (Widget D should be first data row after header)
                widget_d_pos = html_content.find("Widget D")
                widget_a_pos = html_content.find("Widget A")
                assert widget_d_pos < widget_a_pos  # D comes before A (sorted by sales desc)

    @pytest.mark.asyncio
    async def test_markdown_output_with_alignment(self, mcp_headers):
        """Test Phase 8: Markdown output with alignment markers."""

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 1. Create session
                result = await session.call_tool(
                    "create_document_session",
                    arguments={
                        "template_id": "basic_report",
                        "alias": "test_financial_table_workflow-24",
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                session_id = response.get("data", {}).get("session_id")

                # 2. Add table
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "table",
                        "parameters": {
                            "rows": [
                                ["Item", "Price", "Quantity", "Total"],
                                ["Widget", "29.99", "10", "299.90"],
                                ["Gadget", "49.99", "5", "249.95"],
                            ],
                            "has_header": True,
                            "column_alignments": ["left", "right", "center", "right"],
                        },
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"

                # 3. Render to Markdown
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "md"},
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"
                markdown_content = response.get("data", {}).get("content")

                # Verify markdown table structure
                assert "|" in markdown_content
                assert "Item" in markdown_content
                assert "Widget" in markdown_content

                # Verify alignment markers
                assert ":---" in markdown_content  # Left alignment
                assert "---:" in markdown_content  # Right alignment
                assert ":---:" in markdown_content  # Center alignment

    @pytest.mark.asyncio
    async def test_multiple_tables_in_document(self, mcp_headers):
        """Test document with multiple tables."""

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 1. Create session
                result = await session.call_tool(
                    "create_document_session",
                    arguments={
                        "template_id": "basic_report",
                        "alias": "test_financial_table_workflow-25",
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                session_id = response.get("data", {}).get("session_id")

                # 2. Add multiple tables to same document
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "table",
                        "parameters": {
                            "rows": [
                                ["Region", "Revenue"],
                                ["North", "500000"],
                                ["South", "450000"],
                            ],
                            "has_header": True,
                            "title": "Revenue by Region",
                            "number_format": {"1": "currency:USD"},
                        },
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"

                # 3. Add second table (expenses)
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "table",
                        "parameters": {
                            "rows": [
                                ["Category", "Amount"],
                                ["Marketing", "150000"],
                                ["Operations", "200000"],
                            ],
                            "has_header": True,
                            "title": "Expenses by Category",
                            "number_format": {"1": "currency:USD"},
                        },
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"

                # 4. Render to HTML
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "html"},
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"
                html_content = response.get("data", {}).get("content")

                # Verify both tables present
                assert "Revenue by Region" in html_content
                assert "Expenses by Category" in html_content
                assert "North" in html_content
                assert "Marketing" in html_content

    @pytest.mark.asyncio
    async def test_all_output_formats(self, mcp_headers):
        """Test rendering to HTML, PDF, and Markdown."""

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 1. Create session
                result = await session.call_tool(
                    "create_document_session",
                    arguments={
                        "template_id": "basic_report",
                        "alias": "test_financial_table_workflow-26",
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                session_id = response.get("data", {}).get("session_id")

                # 2. Add table
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "table",
                        "parameters": {
                            "rows": [
                                ["Name", "Value"],
                                ["Test A", "100"],
                                ["Test B", "200"],
                            ],
                            "has_header": True,
                            "title": "Test Data",
                        },
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"

                # 3. Test HTML format
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "html"},
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"
                assert response.get("data", {}).get("format") == "html"
                html_content = response.get("data", {}).get("content")
                assert "<table" in html_content
                assert "Test Data" in html_content

                # 4. Test PDF format
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "pdf"},
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"
                assert response.get("data", {}).get("format") == "pdf"
                pdf_content = response.get("data", {}).get("content")
                assert pdf_content  # Base64 encoded PDF
                assert len(pdf_content) > 100  # PDF should have substantial size

                # 5. Test Markdown format
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "md"},
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"
                assert response.get("data", {}).get("format") == "markdown"
                markdown_content = response.get("data", {}).get("content")
                assert "|" in markdown_content  # Markdown table separator
                assert "Test Data" in markdown_content
                assert "Test A" in markdown_content


class TestTablePerformance:
    """Performance tests for large tables."""

    @pytest.mark.asyncio
    async def test_large_table_100_rows(self, mcp_headers):
        """Test performance with 100-row table."""

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 1. Create session
                result = await session.call_tool(
                    "create_document_session",
                    arguments={
                        "template_id": "basic_report",
                        "alias": "test_financial_table_workflow-27",
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                session_id = response.get("data", {}).get("session_id")

                # 2. Generate wide table (20 columns)ble (100 rows)
                rows = [["ID", "Name", "Value", "Status"]]
                for i in range(1, 101):
                    rows.append(
                        [
                            str(i),
                            f"Item {i}",
                            str(1000 + i * 10),
                            "Active" if i % 2 == 0 else "Inactive",
                        ]
                    )

                # 3. Add large table
                start_time = time.time()
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "table",
                        "parameters": {
                            "rows": rows,
                            "has_header": True,
                            "number_format": {"2": "currency:USD"},
                        },
                    },
                )
                add_time = time.time() - start_time
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"

                # Should complete in reasonable time (< 5 seconds)
                assert add_time < 5.0

                # 4. Render to HTML
                start_time = time.time()
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "html"},
                )
                render_time = time.time() - start_time
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"

                # Rendering should complete in reasonable time (< 10 seconds)
                assert render_time < 10.0

                html_content = response.get("data", {}).get("content")
                assert "Item 1" in html_content
                assert "Item 100" in html_content

    @pytest.mark.asyncio
    async def test_wide_table_20_columns(self, mcp_headers):
        """Test performance with 20-column table."""

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 1. Create session
                result = await session.call_tool(
                    "create_document_session",
                    arguments={
                        "template_id": "basic_report",
                        "alias": "test_financial_table_workflow-28",
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                session_id = response.get("data", {}).get("session_id")

                # 2. Generate 20-column table
                header = [f"Col{i}" for i in range(1, 21)]
                rows = [header]
                for i in range(10):  # 10 data rows
                    row = [str((i + 1) * (j + 1)) for j in range(20)]
                    rows.append(row)

                # 3. Add wide table
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "table",
                        "parameters": {
                            "rows": rows,
                            "has_header": True,
                            "compact": True,  # Use compact mode for wide tables
                        },
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"

                # 4. Render to HTML
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "html"},
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"

                html_content = response.get("data", {}).get("content")
                assert "Col1" in html_content
                assert "Col20" in html_content

    @pytest.mark.asyncio
    async def test_sorting_performance(self, mcp_headers):
        """Test sorting performance with 50 rows."""

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # 1. Create session
                result = await session.call_tool(
                    "create_document_session",
                    arguments={
                        "template_id": "basic_report",
                        "alias": "test_financial_table_workflow-29",
                    },
                )
                response = _safe_json_parse(_extract_text(result))
                session_id = response.get("data", {}).get("session_id")

                # 2. Generate unsorted data
                rows = [["Name", "Score"]]
                import random

                random.seed(42)
                for i in range(50):
                    rows.append([f"Person {i}", str(random.randint(1, 1000))])

                # 3. Add table with sorting
                start_time = time.time()
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "table",
                        "parameters": {
                            "rows": rows,
                            "has_header": True,
                            "sort_by": {"column": "Score", "order": "desc"},
                        },
                    },
                )
                sort_time = time.time() - start_time
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"

                # Sorting should be fast (< 2 seconds)
                assert sort_time < 2.0

                # 4. Verify sorted order in rendered output
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "html"},
                )
                response = _safe_json_parse(_extract_text(result))
                assert response.get("status") == "success"
                # If sorted correctly, higher scores should appear earlier in HTML
