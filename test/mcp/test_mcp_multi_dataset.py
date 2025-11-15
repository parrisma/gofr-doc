"""Tests for multi-dataset rendering via MCP protocol"""

import pytest
import base64
import os
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from app.logger import Logger, session_logger


@pytest.fixture
def logger() -> Logger:
    """Create a logger for tests"""
    return session_logger


@pytest.mark.asyncio
async def test_render_two_datasets_mcp(test_jwt_token, logger):
    """Test rendering two datasets via MCP"""
    logger.info("Testing MCP render with two datasets")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "render_graph",
                arguments={
                    "title": "Two Dataset MCP Test",
                    "x": [1, 2, 3, 4, 5],
                    "y1": [10, 20, 15, 25, 30],
                    "y2": [8, 18, 13, 23, 28],
                    "label1": "Series A",
                    "label2": "Series B",
                    "color1": "red",
                    "color2": "blue",
                    "type": "line",
                    "token": test_jwt_token,
                },
            )

            assert result is not None
            assert len(result.content) > 0
            logger.info("Two datasets rendered successfully via MCP")


@pytest.mark.asyncio
async def test_render_three_datasets_bar_mcp(test_jwt_token, logger):
    """Test rendering three datasets as grouped bars via MCP"""
    logger.info("Testing MCP render with three datasets (bar chart)")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "render_graph",
                arguments={
                    "title": "Three Dataset Bar Chart",
                    "y1": [100, 120, 110, 130],
                    "y2": [90, 100, 95, 110],
                    "y3": [80, 95, 85, 100],
                    "label1": "Product A",
                    "label2": "Product B",
                    "label3": "Product C",
                    "type": "bar",
                    "token": test_jwt_token,
                },
            )

            assert result is not None
            assert len(result.content) > 0


@pytest.mark.asyncio
async def test_render_five_datasets_mcp(test_jwt_token, logger):
    """Test rendering maximum five datasets via MCP"""
    logger.info("Testing MCP render with five datasets")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "render_graph",
                arguments={
                    "title": "Five Dataset Test",
                    "x": [1, 2, 3, 4, 5],
                    "y1": [20, 22, 21, 23, 25],
                    "y2": [18, 20, 19, 21, 23],
                    "y3": [22, 24, 23, 25, 27],
                    "y4": [19, 21, 20, 22, 24],
                    "y5": [21, 23, 22, 24, 26],
                    "label1": "Station 1",
                    "label2": "Station 2",
                    "label3": "Station 3",
                    "label4": "Station 4",
                    "label5": "Station 5",
                    "type": "line",
                    "token": test_jwt_token,
                },
            )

            assert result is not None
            assert len(result.content) > 0


@pytest.mark.asyncio
async def test_render_without_x_axis_mcp(test_jwt_token, logger):
    """Test rendering with auto-generated X-axis via MCP"""
    logger.info("Testing MCP render without x-axis (auto-indexed)")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "render_graph",
                arguments={
                    "title": "Auto X-axis Test",
                    "y1": [100, 150, 120, 180],
                    "y2": [80, 120, 100, 150],
                    "label1": "Online",
                    "label2": "In-store",
                    "type": "scatter",
                    "token": test_jwt_token,
                },
            )

            assert result is not None
            assert len(result.content) > 0


@pytest.mark.asyncio
async def test_render_with_axis_controls_mcp(test_jwt_token, logger):
    """Test multi-dataset rendering with axis controls via MCP"""
    logger.info("Testing MCP render with multi-dataset and axis controls")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "render_graph",
                arguments={
                    "title": "Multi-Dataset with Axis Controls",
                    "x": [1, 2, 3, 4, 5, 6],
                    "y1": [20, 25, 22, 28, 24, 30],
                    "y2": [18, 23, 20, 26, 22, 28],
                    "label1": "Forecast",
                    "label2": "Actual",
                    "color1": "red",
                    "color2": "blue",
                    "type": "line",
                    "xmin": 0,
                    "xmax": 7,
                    "ymin": 15,
                    "ymax": 35,
                    "x_major_ticks": [0, 2, 4, 6],
                    "y_major_ticks": [15, 20, 25, 30, 35],
                    "token": test_jwt_token,
                },
            )

            assert result is not None
            assert len(result.content) > 0


@pytest.mark.asyncio
async def test_render_backward_compatible_mcp(test_jwt_token, logger):
    """Test backward compatibility (old 'y' parameter) via MCP"""
    logger.info("Testing MCP render with backward compatible parameters")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "render_graph",
                arguments={
                    "title": "Backward Compatible Test",
                    "x": [1, 2, 3, 4, 5],
                    "y": [10, 20, 15, 25, 30],  # Old parameter
                    "color": "green",  # Old parameter
                    "type": "line",
                    "token": test_jwt_token,
                },
            )

            assert result is not None
            assert len(result.content) > 0


@pytest.mark.asyncio
async def test_render_different_themes_mcp(test_jwt_token, logger):
    """Test multi-dataset rendering with different themes via MCP"""
    logger.info("Testing MCP render with multiple themes")

    themes = ["light", "dark", "bizlight", "bizdark"]

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            for theme in themes:
                result = await session.call_tool(
                    "render_graph",
                    arguments={
                        "title": f"Multi-Dataset {theme} Theme",
                        "y1": [10, 20, 15],
                        "y2": [8, 18, 13],
                        "label1": "A",
                        "label2": "B",
                        "type": "line",
                        "theme": theme,
                        "token": test_jwt_token,
                    },
                )

                assert result is not None
                assert len(result.content) > 0


@pytest.mark.asyncio
async def test_render_proxy_mode_multi_dataset_mcp(test_jwt_token, logger):
    """Test multi-dataset rendering with proxy mode via MCP"""
    logger.info("Testing MCP render with multi-dataset in proxy mode")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "render_graph",
                arguments={
                    "title": "Multi-Dataset Proxy Mode",
                    "y1": [10, 20, 15, 25, 30],
                    "y2": [8, 18, 13, 23, 28],
                    "label1": "Series A",
                    "label2": "Series B",
                    "type": "line",
                    "proxy": True,
                    "token": test_jwt_token,
                },
            )

            assert result is not None
            assert len(result.content) > 0

            # Check for GUID in response
            text_content = str(result.content[0].text)
            assert "guid" in text_content.lower() or "GUID" in text_content


@pytest.mark.asyncio
async def test_validation_mismatched_lengths_mcp(test_jwt_token, logger):
    """Test validation error for mismatched dataset lengths via MCP"""
    logger.info("Testing MCP validation with mismatched lengths")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "render_graph",
                arguments={
                    "title": "Mismatched Lengths",
                    "y1": [10, 20, 15],
                    "y2": [8, 18],  # Different length
                    "type": "line",
                    "token": test_jwt_token,
                },
            )

            # Should return validation error
            text_content = str(result.content[0].text)
            assert "validation" in text_content.lower() or "error" in text_content.lower()
            assert "length" in text_content.lower()
