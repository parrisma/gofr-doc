#!/usr/bin/env python3
"""
Test MCP server rendering functionality with pytest.
Tests various chart types, themes, and validation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from app.logger import Logger, session_logger


MCP_URL = "http://localhost:8011/mcp/"


@pytest.mark.asyncio
async def test_list_tools():
    """Test that MCP server exposes expected tools"""
    logger: Logger = session_logger
    logger.info("Testing MCP server tool listing")

    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info("MCP server initialized successfully")

            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]

            assert len(tool_names) > 0, "No tools found"
            assert "render_graph" in tool_names, "render_graph tool not found"

            logger.info(f"Found {len(tool_names)} tools")


@pytest.mark.asyncio
async def test_render_line_chart():
    """Test rendering a line chart"""
    logger: Logger = session_logger
    logger.info("Testing line chart rendering")

    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            line_args = {
                "title": "Test Line Chart",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10],
                "xlabel": "X Axis",
                "ylabel": "Y Axis",
                "type": "line",
            }

            result = await session.call_tool("render_graph", line_args)
            assert len(result.content) > 0, "No content returned"
            logger.info(f"Line chart rendered successfully")


@pytest.mark.asyncio
async def test_render_bar_chart():
    """Test rendering a bar chart"""
    logger: Logger = session_logger
    logger.info("Testing bar chart rendering")

    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            bar_args = {
                "title": "Test Bar Chart",
                "x": [1, 2, 3, 4, 5],
                "y": [5, 8, 3, 7, 4],
                "xlabel": "Categories",
                "ylabel": "Values",
                "type": "bar",
            }

            result = await session.call_tool("render_graph", bar_args)
            assert len(result.content) > 0, "No content returned"
            logger.info(f"Bar chart rendered successfully")


@pytest.mark.asyncio
async def test_render_scatter_plot():
    """Test rendering a scatter plot"""
    logger: Logger = session_logger
    logger.info("Testing scatter plot rendering")

    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            scatter_args = {
                "title": "Test Scatter Plot",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 5, 3, 8, 6],
                "xlabel": "X Values",
                "ylabel": "Y Values",
                "type": "scatter",
            }

            result = await session.call_tool("render_graph", scatter_args)
            assert len(result.content) > 0, "No content returned"
            logger.info(f"Scatter plot rendered successfully")


@pytest.mark.asyncio
async def test_render_with_dark_theme():
    """Test rendering with dark theme"""
    logger: Logger = session_logger
    logger.info("Testing dark theme rendering")

    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            dark_args = {
                "title": "Dark Theme Chart",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10],
                "type": "line",
                "theme": "dark",
            }

            result = await session.call_tool("render_graph", dark_args)
            assert len(result.content) > 0, "No content returned"
            logger.info(f"Dark theme chart rendered successfully")


@pytest.mark.asyncio
async def test_validation_mismatched_arrays(test_jwt_token):
    """Test validation catches mismatched array lengths"""
    logger: Logger = session_logger
    logger.info("Testing validation for mismatched arrays")

    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            error_args = {
                "title": "Mismatched Arrays",
                "x": [1, 2, 3],
                "y": [1, 2],
                "type": "line",
                "token": test_jwt_token,
            }

            result = await session.call_tool("render_graph", error_args)
            assert len(result.content) > 0, "No content returned"

            error_content = result.content[0]
            if hasattr(error_content, "text"):
                error_text = error_content.text  # type: ignore
            else:
                error_text = str(error_content)

            assert "validation" in error_text.lower(), "Expected validation error"
            assert "length" in error_text.lower(), "Expected length error"
            logger.info("Validation correctly caught mismatched arrays")


@pytest.mark.asyncio
async def test_validation_invalid_chart_type(test_jwt_token):
    """Test validation catches invalid chart type"""
    logger: Logger = session_logger
    logger.info("Testing validation for invalid chart type")

    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            error_args = {
                "title": "Invalid Type",
                "x": [1, 2, 3],
                "y": [1, 2, 3],
                "type": "pie",
                "token": test_jwt_token,
            }

            result = await session.call_tool("render_graph", error_args)


@pytest.mark.asyncio
async def test_validation_empty_arrays(test_jwt_token):
    """Test validation catches empty arrays"""
    logger: Logger = session_logger
    logger.info("Testing validation for empty arrays")

    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            empty_args = {
                "title": "Empty Arrays",
                "x": [],
                "y": [],
                "type": "line",
                "token": test_jwt_token,
            }

            result = await session.call_tool("render_graph", empty_args)
            assert len(result.content) > 0, "No content returned"

            empty_content = result.content[0]
            if hasattr(empty_content, "text"):
                empty_text = empty_content.text  # type: ignore
            else:
                empty_text = str(empty_content)

            assert "validation" in empty_text.lower(), "Expected validation error"
            assert "empty" in empty_text.lower(), "Expected empty error"
            logger.info("Validation correctly caught empty arrays")


@pytest.mark.asyncio
async def test_validation_invalid_alpha(test_jwt_token):
    """Test validation catches invalid alpha value"""
    logger: Logger = session_logger
    logger.info("Testing validation for invalid alpha")

    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            alpha_args = {
                "title": "Invalid Alpha",
                "x": [1, 2, 3],
                "y": [1, 2, 3],
                "alpha": 1.5,
                "token": test_jwt_token,
            }

            result = await session.call_tool("render_graph", alpha_args)
            assert len(result.content) > 0, "No content returned"

            alpha_content = result.content[0]
            if hasattr(alpha_content, "text"):
                alpha_text = alpha_content.text  # type: ignore
            else:
                alpha_text = str(alpha_content)

            assert "validation" in alpha_text.lower(), "Expected validation error"
            assert "alpha" in alpha_text.lower(), "Expected alpha error"
            logger.info("Validation correctly caught invalid alpha")
