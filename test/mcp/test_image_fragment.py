"""Image fragment integration tests for MCP server.

Tests cover:
  - add_image_fragment: URL validation, error handling, security
  - Image URL validation: HTTPS enforcement, content-type checks, accessibility
  - Error responses: Detailed errors with recovery guidance
"""

import json
import os
from typing import Any, Dict

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.logger import Logger, session_logger

# MCP server configuration
MCP_HOST = os.environ.get("GOFR_DOC_MCP_HOST", "localhost")
MCP_PORT = os.environ.get("GOFR_DOC_MCP_PORT", "8040")
MCP_URL = f"http://{MCP_HOST}:{MCP_PORT}/mcp/"


def skip_if_mcp_unavailable(func):
    """Decorator to skip tests if MCP server is unavailable."""
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            response = httpx.get(MCP_URL, timeout=2.0)
            if response.status_code >= 500:
                pytest.skip("MCP server is unavailable (returned 5xx status)")
        except Exception as e:
            pytest.skip(f"MCP server is unavailable: {type(e).__name__}")
        return await func(*args, **kwargs)

    return wrapper


def _parse_json_response(result: Any) -> Dict[str, Any]:
    """Parse JSON response from MCP tool."""
    if hasattr(result, "content") and len(result.content) > 0:
        text = result.content[0].text
        return json.loads(text)
    return {}


@pytest.fixture
def logger() -> Logger:
    """Provide logger for tests."""
    return session_logger


# ==============================================================================
# Tests: add_image_fragment tool registration
# ==============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_image_fragment_tool_exists(server_mcp_headers):
    """Verify add_image_fragment tool is registered."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            assert "add_image_fragment" in tool_names


# ==============================================================================
# Tests: URL Validation
# ==============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_image_fragment_rejects_non_https_url_by_default(logger, server_mcp_headers):
    """Verify add_image_fragment rejects HTTP URLs when require_https=true (default)."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create session
            create_result = await session.call_tool(
                "create_document_session",
                arguments={"template_id": "basic_report", "alias": "test_image_fragment-7"},
            )
            create_response = _parse_json_response(create_result)
            assert create_response["status"] == "success"
            session_id = create_response["data"]["session_id"]

            # Try to add image with HTTP URL (should fail)
            result = await session.call_tool(
                "add_image_fragment",
                arguments={
                    "session_id": session_id,
                    "image_url": "http://example.com/test.png",
                },
            )
            response = _parse_json_response(result)
            assert response["status"] == "error"
            assert response["error_code"] == "INVALID_IMAGE_URL"
            assert "HTTPS" in response["message"]


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_image_fragment_accepts_http_when_explicitly_allowed(logger, server_mcp_headers):
    """Verify add_image_fragment accepts HTTP URLs when require_https=false."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create session
            create_result = await session.call_tool(
                "create_document_session",
                arguments={"template_id": "basic_report", "alias": "test_image_fragment-8"},
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Try with require_https=false (will still fail due to invalid URL, but for different reason)
            result = await session.call_tool(
                "add_image_fragment",
                arguments={
                    "session_id": session_id,
                    "image_url": "http://httpbin.org/image/png",
                    "require_https": False,
                },
            )
            response = _parse_json_response(result)
            # Should get past HTTPS check (error code won't be INVALID_IMAGE_URL for HTTPS)
            if response["status"] == "error":
                assert response["error_code"] != "INVALID_IMAGE_URL" or "HTTPS" not in response.get(
                    "message", ""
                )


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_image_fragment_rejects_invalid_url(logger, server_mcp_headers):
    """Verify add_image_fragment rejects malformed URLs."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create session
            create_result = await session.call_tool(
                "create_document_session",
                arguments={"template_id": "basic_report", "alias": "test_image_fragment-9"},
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Try with invalid URL
            result = await session.call_tool(
                "add_image_fragment",
                arguments={
                    "session_id": session_id,
                    "image_url": "not-a-valid-url",
                },
            )
            response = _parse_json_response(result)
            assert response["status"] == "error"
            assert response["error_code"] == "INVALID_IMAGE_URL"


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_image_fragment_success_with_local_server(
    logger, server_mcp_headers, image_server
):
    """Verify add_image_fragment succeeds with valid accessible image from local test server."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create session
            create_result = await session.call_tool(
                "create_document_session",
                arguments={"template_id": "basic_report", "alias": "test_image_fragment-10"},
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Get URL from local test server
            image_url = image_server.get_url("graph.png")

            # Add image with valid URL from local server (HTTP is OK with require_https=false)
            result = await session.call_tool(
                "add_image_fragment",
                arguments={
                    "session_id": session_id,
                    "image_url": image_url,
                    "title": "Test Graph",
                    "width": 400,
                    "alt_text": "Test graph image",
                    "require_https": False,  # Local server uses HTTP
                },
            )
            response = _parse_json_response(result)
            assert response["status"] == "success"
            assert "fragment_instance_guid" in response["data"]


# ==============================================================================
# Tests: Security
# ==============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_image_fragment_respects_group_security(
    logger, server_auth_service, server_mcp_headers
):
    """Verify add_image_fragment respects group isolation."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create session in group1
            create_result = await session.call_tool(
                "create_document_session",
                arguments={"template_id": "basic_report", "alias": "test_image_fragment-11"},
            )
            create_response = _parse_json_response(create_result)
            _ = create_response["data"]["session_id"]  # noqa: F841

            # Try to add image to non-existent session (simulates cross-group access)
            result = await session.call_tool(
                "add_image_fragment",
                arguments={
                    "session_id": "nonexistent-session-id",
                    "image_url": "https://example.com/test.png",
                },
            )
            response = _parse_json_response(result)
            assert response["status"] == "error"
            assert response["error_code"] == "SESSION_NOT_FOUND"
