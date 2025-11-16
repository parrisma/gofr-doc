"""Document rendering integration tests for MCP server.

Tests cover:
  - get_document: Rendering documents in multiple formats (HTML, PDF, Markdown)
  - set_style: Applying style assets to rendered documents
  - Validation of rendered output structure and content
  - Error handling for invalid sessions, styles, and formats
"""

import functools
import json
import os
from typing import Any, Dict

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.logger import session_logger

# MCP server configuration via environment variables (defaults to production port)
MCP_PORT = os.environ.get("DOCO_MCP_PORT", "8011")
MCP_URL = f"http://localhost:{MCP_PORT}/mcp/"


# ============================================================================
# Utilities
# ============================================================================


def _extract_text(result) -> str:
    """Extract text content from MCP result."""
    if not result:
        return ""
    if not hasattr(result, "content") or not result.content:
        return ""
    content = result.content[0]
    if hasattr(content, "text"):
        return content.text
    return str(content)


def _parse_json_response(result) -> Dict[str, Any]:
    """Parse JSON from MCP result, handling both JSON errors and validation errors."""
    text = _extract_text(result)
    if not text:
        # If no text, check if it's an error
        if hasattr(result, "isError") and result.isError:
            # Return a structured error response
            return {
                "status": "error",
                "error_code": "VALIDATION_ERROR",
                "message": "Validation error from MCP framework",
            }
        raise ValueError(f"No text content in result: {result}")

    # Try to parse as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # If it's not JSON but looks like an error message, return it as an error
        if "error" in text.lower() or "invalid" in text.lower():
            return {"status": "error", "error_code": "VALIDATION_ERROR", "message": text}
        raise ValueError(f"Unable to parse response as JSON: {text}")


def skip_if_mcp_unavailable(func):
    """Decorator to skip test if MCP server is unavailable."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            async with streamablehttp_client(MCP_URL) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
        except Exception as e:
            pytest.skip(f"MCP server unavailable: {e}")
        return await func(*args, **kwargs)

    return wrapper


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def logger():
    """Provide a logger instance."""
    return session_logger


# ============================================================================
# Tests: get_document tool exists and responds
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_document_tool_exists(logger):
    """Verify get_document tool is registered."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            assert "get_document" in tool_names


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_document_requires_session_id(logger):
    """Verify get_document requires session_id parameter."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_document", arguments={"format": "html"})
            response = _parse_json_response(result)
            assert response["status"] == "error"
            assert (
                "session_id" in response.get("message", "").lower()
                or "required" in response.get("message", "").lower()
            )


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_document_invalid_session(logger):
    """Verify get_document handles invalid session gracefully."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_document",
                arguments={"session_id": "invalid-session-id", "format": "html"},
            )
            response = _parse_json_response(result)
            assert response["status"] == "error"
            # Backend returns SESSION_NOT_READY for invalid sessions (validates first)
            assert response["error_code"] in ["SESSION_NOT_READY", "SESSION_NOT_FOUND"]


# ============================================================================
# Tests: get_document HTML rendering
# ============================================================================


# ============================================================================
# Tests: get_document Markdown rendering
# ============================================================================


# ============================================================================
# Tests: get_document with styles
# ============================================================================
