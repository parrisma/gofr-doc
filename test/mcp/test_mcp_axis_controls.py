"""Tests for MCP server axis control parameters"""

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from app.auth.service import AuthService
from app.logger import Logger, session_logger


@pytest.fixture
def test_jwt_token():
    """Create a JWT token for testing"""
    auth_service = AuthService(
        secret_key="test-secret-key-for-auth-testing",
        token_store_path="/tmp/doco_test_tokens.json",
    )
    token = auth_service.create_token(group="test_group")
    return token


@pytest.fixture
def logger() -> Logger:
    """Create a logger for tests"""
    return session_logger


@pytest.mark.asyncio
async def test_render_with_axis_limits(test_jwt_token, logger):
    """Test rendering with axis limits via MCP"""
    http_url = "http://localhost:8011/mcp/"

    async with streamablehttp_client(http_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call render_graph with axis limits
            args = {
                "title": "Chart with Axis Limits",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10],
                "type": "line",
                "xmin": 0,
                "xmax": 6,
                "ymin": 0,
                "ymax": 12,
                "token": test_jwt_token,
            }

            result = await session.call_tool("render_graph", args)

            assert len(result.content) >= 1
            # Check for image content
            image_found = False
            for content in result.content:
                if content.type == "image":
                    image_found = True
                    assert content.data is not None
                    logger.info("Chart with axis limits rendered successfully")
                    break

            assert image_found, "No image content in response"


@pytest.mark.asyncio
async def test_render_with_major_ticks(test_jwt_token, logger):
    """Test rendering with custom major ticks via MCP"""
    http_url = "http://localhost:8011/mcp/"

    async with streamablehttp_client(http_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call render_graph with major ticks
            args = {
                "title": "Chart with Major Ticks",
                "x": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                "y": [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
                "type": "line",
                "x_major_ticks": [0, 5, 10],
                "y_major_ticks": [0, 25, 50],
                "token": test_jwt_token,
            }

            result = await session.call_tool("render_graph", args)

            assert len(result.content) >= 1
            image_found = False
            for content in result.content:
                if content.type == "image":
                    image_found = True
                    assert content.data is not None
                    logger.info("Chart with major ticks rendered successfully")
                    break

            assert image_found, "No image content in response"


@pytest.mark.asyncio
async def test_render_with_minor_ticks(test_jwt_token, logger):
    """Test rendering with major and minor ticks via MCP"""
    http_url = "http://localhost:8011/mcp/"

    async with streamablehttp_client(http_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call render_graph with both major and minor ticks
            args = {
                "title": "Chart with Minor Ticks",
                "x": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                "y": [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
                "type": "scatter",
                "x_major_ticks": [0, 5, 10],
                "x_minor_ticks": [1, 2, 3, 4, 6, 7, 8, 9],
                "y_major_ticks": [0, 25, 50],
                "y_minor_ticks": [10, 15, 20, 30, 35, 40],
                "token": test_jwt_token,
            }

            result = await session.call_tool("render_graph", args)

            assert len(result.content) >= 1
            image_found = False
            for content in result.content:
                if content.type == "image":
                    image_found = True
                    assert content.data is not None
                    logger.info("Chart with minor ticks rendered successfully")
                    break

            assert image_found, "No image content in response"


@pytest.mark.asyncio
async def test_render_with_all_axis_controls(test_jwt_token, logger):
    """Test rendering with all axis control parameters via MCP"""
    http_url = "http://localhost:8011/mcp/"

    async with streamablehttp_client(http_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call render_graph with all axis controls
            args = {
                "title": "Chart with All Controls",
                "x": [1, 2, 3, 4, 5, 6, 7, 8],
                "y": [10, 20, 15, 25, 30, 22, 28, 35],
                "type": "line",
                "xmin": 0,
                "xmax": 9,
                "ymin": 5,
                "ymax": 40,
                "x_major_ticks": [0, 3, 6, 9],
                "y_major_ticks": [10, 20, 30, 40],
                "x_minor_ticks": [1, 2, 4, 5, 7, 8],
                "y_minor_ticks": [15, 25, 35],
                "color": "#2E86AB",
                "line_width": 2.5,
                "theme": "dark",
                "token": test_jwt_token,
            }

            result = await session.call_tool("render_graph", args)

            assert len(result.content) >= 1
            image_found = False
            for content in result.content:
                if content.type == "image":
                    image_found = True
                    assert content.data is not None
                    logger.info("Chart with all axis controls rendered successfully")
                    break

            assert image_found, "No image content in response"


@pytest.mark.asyncio
async def test_render_with_partial_limits(test_jwt_token, logger):
    """Test rendering with only some axis limits set via MCP"""
    http_url = "http://localhost:8011/mcp/"

    async with streamablehttp_client(http_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call render_graph with partial limits
            args = {
                "title": "Chart with Partial Limits",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10],
                "type": "bar",
                "ymin": 0,  # Only set minimum y
                "token": test_jwt_token,
            }

            result = await session.call_tool("render_graph", args)

            assert len(result.content) >= 1
            image_found = False
            for content in result.content:
                if content.type == "image":
                    image_found = True
                    assert content.data is not None
                    logger.info("Chart with partial limits rendered successfully")
                    break

            assert image_found, "No image content in response"


@pytest.mark.asyncio
async def test_render_without_axis_controls(test_jwt_token, logger):
    """Test that rendering without axis controls still works (backward compatibility)"""
    http_url = "http://localhost:8011/mcp/"

    async with streamablehttp_client(http_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call render_graph without any axis controls
            args = {
                "title": "Chart without Controls",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10],
                "type": "line",
                "token": test_jwt_token,
            }

            result = await session.call_tool("render_graph", args)

            assert len(result.content) >= 1
            image_found = False
            for content in result.content:
                if content.type == "image":
                    image_found = True
                    assert content.data is not None
                    logger.info(
                        "Chart without controls rendered successfully (backward compatible)"
                    )
                    break

            assert image_found, "No image content in response"
