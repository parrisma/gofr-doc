"""Tests for MCP document discovery tools.

Phase 1: Discovery & Metadata Tools
Tests: list_templates, get_template_details, list_template_fragments, get_fragment_details, list_styles
"""

import json
import os
import pytest
import httpx
import functools
from typing import Any, Dict
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent
from app.logger import Logger, session_logger

# Port configuration via environment variables (defaults to production port)
MCP_PORT = os.environ.get("GOFR_DOC_MCP_PORT", "8040")
MCP_URL = f"http://localhost:{MCP_PORT}/mcp/"

# Note: auth_service and mcp_headers fixtures are now provided by conftest.py


def skip_if_mcp_unavailable(func):
    """Decorator to skip tests if MCP server is unavailable."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):  # type: ignore
        try:
            response = httpx.get(MCP_URL, timeout=2.0)
            if response.status_code >= 500:
                pytest.skip("MCP server is unavailable (returned 5xx status)")
        except Exception as e:
            pytest.skip(f"MCP server is unavailable: {type(e).__name__}")
        return await func(*args, **kwargs)

    return wrapper


def _extract_text(result: Any) -> str:
    """Extract text from MCP tool result."""
    if not result or not result.content:
        return ""
    content = result.content[0]
    if isinstance(content, TextContent):
        return content.text
    return str(content)


def _parse_json_response(result: Any) -> Dict[str, Any]:
    """Parse JSON response from MCP tool."""
    text = _extract_text(result)
    if not text:
        raise ValueError("Empty response from tool")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON response: {text}") from e


@pytest.fixture
def logger() -> Logger:
    """Provide logger for tests."""
    return session_logger


# ==============================================================================
# list_templates Tests
# ==============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_list_templates_tool_exists(mcp_headers):
    """Test that list_templates tool is available in MCP server."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get list of tools
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]

            # Verify list_templates is in the tools
            assert "list_templates" in tool_names, "list_templates tool not found in MCP server"


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_list_templates_returns_templates(logger, mcp_headers):
    """Test that list_templates returns available templates."""
    logger.info("Testing list_templates tool")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call list_templates with no arguments
            result = await session.call_tool("list_templates", arguments={})

            assert result is not None
            assert len(result.content) > 0

            # Should return text content with JSON
            text_content = _extract_text(result)
            assert len(text_content) > 0

            # Should contain status and data
            assert "status" in text_content.lower()
            logger.info(f"List templates response: {text_content[:100]}...")


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_list_templates_response_structure(logger, mcp_headers):
    """Test that list_templates returns properly structured response."""
    logger.info("Testing list_templates response structure")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("list_templates", arguments={})
            response = _parse_json_response(result)

            # Should have status
            assert "status" in response
            assert response["status"] == "success"

            # Should have data with templates
            assert "data" in response
            assert "templates" in response["data"]

            # Each template should have required fields
            templates = response["data"]["templates"]
            if len(templates) > 0:
                for template in templates:
                    assert "template_id" in template
                    assert "name" in template
                    assert "description" in template
                    assert "group" in template

            logger.info(f"Found {len(templates)} templates")


# ==============================================================================
# get_template_details Tests
# ==============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_template_details_tool_exists(mcp_headers):
    """Test that get_template_details tool is available."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]

            assert "get_template_details" in tool_names


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_template_details_requires_template_id(mcp_headers):
    """Test that get_template_details requires template_id parameter."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call without template_id should fail validation
            try:
                result = await session.call_tool("get_template_details", arguments={})
                response = _parse_json_response(result)

                # Should get validation error
                assert response["status"] == "error"
                assert "INVALID_ARGUMENTS" in response.get("error_code", "")
            except Exception as e:
                # Validation error is expected
                assert "template_id" in str(e).lower() or "validation" in str(e).lower()


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_template_details_invalid_template(logger, mcp_headers):
    """Test that get_template_details returns error for non-existent template."""
    logger.info("Testing get_template_details with invalid template")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "get_template_details", arguments={"template_id": "nonexistent_template"}
            )

            response = _parse_json_response(result)

            # Should return error status
            assert response["status"] == "error"
            assert "TEMPLATE_NOT_FOUND" in response.get("error_code", "")
            assert "recovery_strategy" in response  # Error handling validation

            logger.info("Correctly returned error for invalid template")


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_template_details_returns_schema(logger, mcp_headers):
    """Test that get_template_details returns template schema with global parameters."""
    logger.info("Testing get_template_details returns schema")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # First get available templates
            list_result = await session.call_tool("list_templates", arguments={})
            list_response = _parse_json_response(list_result)

            templates = list_response["data"]["templates"]
            if len(templates) == 0:
                pytest.skip("No templates available for testing")

            # Get details for first template
            template_id = templates[0]["template_id"]
            details_result = await session.call_tool(
                "get_template_details", arguments={"template_id": template_id}
            )

            details_response = _parse_json_response(details_result)

            # Log response for debugging
            logger.info(f"Template details response: {details_response}")

            # Should return success
            assert (
                details_response["status"] == "success"
            ), f"Expected success but got {details_response}"

            # Should have template details
            data = details_response["data"]
            assert "template_id" in data
            assert "name" in data
            assert "description" in data
            assert "global_parameters" in data

            logger.info(
                f"Template {template_id} has {len(data.get('global_parameters', []))} global parameters"
            )


# ==============================================================================
# list_template_fragments Tests
# ==============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_list_template_fragments_tool_exists(mcp_headers):
    """Test that list_template_fragments tool is available."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]

            assert "list_template_fragments" in tool_names


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_list_template_fragments_requires_template_id(mcp_headers):
    """Test that list_template_fragments requires template_id parameter."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call without template_id should fail validation
            try:
                result = await session.call_tool("list_template_fragments", arguments={})
                response = _parse_json_response(result)
                assert response["status"] == "error"
            except Exception as e:
                assert "template_id" in str(e).lower() or "validation" in str(e).lower()


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_list_template_fragments_returns_fragments(logger, mcp_headers):
    """Test that list_template_fragments returns fragment list."""
    logger.info("Testing list_template_fragments")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get first template
            list_result = await session.call_tool("list_templates", arguments={})
            list_response = _parse_json_response(list_result)

            templates = list_response["data"]["templates"]
            if len(templates) == 0:
                pytest.skip("No templates available for testing")

            template_id = templates[0]["template_id"]

            # Get fragments for template
            result = await session.call_tool(
                "list_template_fragments", arguments={"template_id": template_id}
            )

            response = _parse_json_response(result)

            assert response["status"] == "success"
            assert "template_id" in response["data"]
            assert response["data"]["template_id"] == template_id
            assert "fragments" in response["data"]

            fragments = response["data"]["fragments"]
            logger.info(f"Template {template_id} has {len(fragments)} fragments")

            # Each fragment should have required fields
            for fragment in fragments:
                assert "fragment_id" in fragment
                assert "name" in fragment
                assert "description" in fragment
                assert "parameter_count" in fragment


# ==============================================================================
# get_fragment_details Tests
# ==============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_fragment_details_tool_exists(mcp_headers):
    """Test that get_fragment_details tool is available."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]

            assert "get_fragment_details" in tool_names


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_fragment_details_requires_parameters(mcp_headers):
    """Test that get_fragment_details requires template_id and fragment_id."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call without parameters should fail
            try:
                result = await session.call_tool("get_fragment_details", arguments={})
                response = _parse_json_response(result)
                assert response["status"] == "error"
            except Exception as e:
                # Validation error expected
                assert "validation" in str(e).lower() or "required" in str(e).lower()


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_fragment_details_invalid_fragment(logger, mcp_headers):
    """Test that get_fragment_details returns error for non-existent fragment."""
    logger.info("Testing get_fragment_details with invalid fragment")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get first template
            list_result = await session.call_tool("list_templates", arguments={})
            list_response = _parse_json_response(list_result)

            templates = list_response["data"]["templates"]
            if len(templates) == 0:
                pytest.skip("No templates available for testing")

            template_id = templates[0]["template_id"]

            # Request non-existent fragment
            result = await session.call_tool(
                "get_fragment_details",
                arguments={"template_id": template_id, "fragment_id": "nonexistent_fragment"},
            )

            response = _parse_json_response(result)

            # Should return error
            assert response["status"] == "error"
            assert "FRAGMENT_NOT_FOUND" in response.get("error_code", "")

            logger.info("Correctly returned error for invalid fragment")


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_fragment_details_returns_schema(logger, mcp_headers):
    """Test that get_fragment_details returns fragment parameter schema."""
    logger.info("Testing get_fragment_details returns schema")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get first template with fragments
            list_result = await session.call_tool("list_templates", arguments={})
            list_response = _parse_json_response(list_result)

            templates = list_response["data"]["templates"]
            if len(templates) == 0:
                pytest.skip("No templates available for testing")

            template_id = templates[0]["template_id"]

            # Get fragments
            frag_result = await session.call_tool(
                "list_template_fragments", arguments={"template_id": template_id}
            )
            frag_response = _parse_json_response(frag_result)

            fragments = frag_response["data"]["fragments"]
            if len(fragments) == 0:
                pytest.skip(f"Template {template_id} has no fragments")

            fragment_id = fragments[0]["fragment_id"]

            # Get fragment details
            details_result = await session.call_tool(
                "get_fragment_details",
                arguments={"template_id": template_id, "fragment_id": fragment_id},
            )

            details_response = _parse_json_response(details_result)

            assert details_response["status"] == "success"

            # Should have fragment details
            data = details_response["data"]
            assert "template_id" in data
            assert "fragment_id" in data
            assert "name" in data
            assert "description" in data
            assert "parameters" in data

            logger.info(f"Fragment {fragment_id} has {len(data.get('parameters', []))} parameters")


# ==============================================================================
# list_styles Tests
# ==============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_list_styles_tool_exists(mcp_headers):
    """Test that list_styles tool is available."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]

            assert "list_styles" in tool_names


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_list_styles_returns_styles(logger, mcp_headers):
    """Test that list_styles returns available styles."""
    logger.info("Testing list_styles tool")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call list_styles with no arguments
            result = await session.call_tool("list_styles", arguments={})

            assert result is not None
            assert len(result.content) > 0

            # Should return text content with JSON
            text_content = _extract_text(result)
            assert len(text_content) > 0

            # Parse response
            response = _parse_json_response(result)

            assert response["status"] == "success"
            assert "styles" in response["data"]

            styles = response["data"]["styles"]
            logger.info(f"Found {len(styles)} available styles")

            # Each style should have required fields
            for style in styles:
                assert "style_id" in style
                assert "name" in style
                assert "description" in style
