"""Tests for MCP list_themes tool"""

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from app.logger import Logger, session_logger


@pytest.fixture
def logger() -> Logger:
    """Create a logger for tests"""
    return session_logger


@pytest.mark.asyncio
async def test_list_themes_tool_exists():
    """Test that list_themes tool is available in MCP server"""
    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get list of tools
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]

            # Verify list_themes is in the tools
            assert "list_themes" in tool_names, "list_themes tool not found in MCP server"


@pytest.mark.asyncio
async def test_list_themes_tool_no_parameters(logger):
    """Test that list_themes tool requires no parameters"""
    logger.info("Testing list_themes tool")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call list_themes with no arguments
            result = await session.call_tool("list_themes", arguments={})

            assert result is not None
            assert len(result.content) > 0

            # Should return text content
            text_content = str(result.content[0].text)
            assert len(text_content) > 0
            logger.info(f"List themes response: {text_content[:100]}...")


@pytest.mark.asyncio
async def test_list_themes_returns_all_themes(logger):
    """Test that list_themes returns all expected themes"""
    logger.info("Testing list_themes returns all themes")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("list_themes", arguments={})
            text_content = str(result.content[0].text)

            # Check that all expected themes are present
            expected_themes = ["light", "dark", "bizlight", "bizdark"]
            for theme in expected_themes:
                assert (
                    theme in text_content.lower()
                ), f"Theme {theme} not found in list_themes output"

            logger.info(f"All {len(expected_themes)} themes found in output")


@pytest.mark.asyncio
async def test_list_themes_includes_descriptions(logger):
    """Test that list_themes includes descriptions for each theme"""
    logger.info("Testing list_themes includes descriptions")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("list_themes", arguments={})
            text_content = str(result.content[0].text)

            # Each theme should have a colon followed by description
            assert "light:" in text_content.lower()
            assert "dark:" in text_content.lower()
            assert "bizlight:" in text_content.lower()
            assert "bizdark:" in text_content.lower()

            # Check for some description keywords
            assert any(word in text_content.lower() for word in ["bright", "clean", "presentation"])
            assert any(word in text_content.lower() for word in ["strain", "muted", "low-light"])
            assert any(
                word in text_content.lower() for word in ["business", "professional", "corporate"]
            )

            logger.info("All themes have descriptions")


@pytest.mark.asyncio
async def test_list_themes_formatted_correctly(logger):
    """Test that list_themes output is properly formatted"""
    logger.info("Testing list_themes formatting")

    async with streamablehttp_client("http://localhost:8011/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("list_themes", arguments={})
            text_content = str(result.content[0].text)

            # Should have a header
            assert "Available Themes" in text_content or "available themes" in text_content.lower()

            # Should use bullet points or similar formatting
            assert "•" in text_content or "-" in text_content or "*" in text_content

            # Should have multiple lines (one per theme plus header)
            lines = text_content.split("\n")
            assert len(lines) >= 5  # Header + 4 themes

            logger.info(f"Output has {len(lines)} lines and is properly formatted")
