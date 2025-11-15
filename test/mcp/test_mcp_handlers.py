"""Tests for MCP list_handlers tool"""

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from app.logger import Logger, session_logger


@pytest.fixture
def logger() -> Logger:
    """Create a logger for tests"""
    return session_logger


@pytest.mark.asyncio
async def test_list_handlers_tool_exists():
    """Test that list_handlers tool is available in MCP server"""
    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get list of tools
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]

            # Verify list_handlers is in the tools
            assert "list_handlers" in tool_names, "list_handlers tool not found in MCP server"


@pytest.mark.asyncio
async def test_list_handlers_tool_no_parameters(logger):
    """Test that list_handlers tool requires no parameters"""
    logger.info("Testing list_handlers tool")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call list_handlers with no arguments
            result = await session.call_tool("list_handlers", arguments={})

            assert result is not None
            assert len(result.content) > 0

            # Should return text content
            text_content = str(result.content[0].text)
            assert len(text_content) > 0
            logger.info(f"List handlers response: {text_content[:100]}...")


@pytest.mark.asyncio
async def test_list_handlers_returns_all_handlers(logger):
    """Test that list_handlers returns all expected graph types"""
    logger.info("Testing list_handlers returns all handlers")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("list_handlers", arguments={})
            text_content = str(result.content[0].text)

            # Check that all expected handlers are present
            expected_handlers = ["line", "scatter", "bar"]
            for handler in expected_handlers:
                assert (
                    handler in text_content.lower()
                ), f"Handler {handler} not found in list_handlers output"

            logger.info(f"All {len(expected_handlers)} handlers found in output")


@pytest.mark.asyncio
async def test_list_handlers_includes_descriptions(logger):
    """Test that list_handlers includes descriptions for each graph type"""
    logger.info("Testing list_handlers includes descriptions")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("list_handlers", arguments={})
            text_content = str(result.content[0].text)

            # Each handler should have a colon followed by description
            assert "line:" in text_content.lower()
            assert "scatter:" in text_content.lower()
            assert "bar:" in text_content.lower()

            # Check for some description keywords
            assert any(word in text_content.lower() for word in ["trend", "continuous", "chart"])
            assert any(
                word in text_content.lower() for word in ["relationship", "correlation", "pattern"]
            )
            assert any(word in text_content.lower() for word in ["categor", "compar", "grouped"])

            logger.info("All handlers have descriptions")


@pytest.mark.asyncio
async def test_list_handlers_formatted_correctly(logger):
    """Test that list_handlers output is properly formatted"""
    logger.info("Testing list_handlers formatting")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("list_handlers", arguments={})
            text_content = str(result.content[0].text)

            # Should have a header
            assert (
                "Available Graph Types" in text_content
                or "available graph types" in text_content.lower()
            )

            # Should use bullet points or similar formatting
            assert "•" in text_content or "-" in text_content or "*" in text_content

            # Should have multiple lines (one per handler plus header)
            lines = text_content.split("\n")
            assert len(lines) >= 4  # Header + 3 handlers

            logger.info(f"Output has {len(lines)} lines and is properly formatted")
