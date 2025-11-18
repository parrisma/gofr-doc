"""Fragment management integration tests for MCP server.

Tests cover:
  - add_fragment: Adding fragment instances to document sessions
  - remove_fragment: Removing fragment instances from sessions
  - list_session_fragments: Listing fragments currently in a session
"""

import json
import os
from typing import Any, Dict

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent

from app.logger import Logger, session_logger

# MCP server configuration via environment variables (defaults to production port)
MCP_PORT = os.environ.get("DOCO_MCP_PORT", "8011")
MCP_URL = f"http://localhost:{MCP_PORT}/mcp/"

# Note: auth_service and mcp_headers fixtures are now provided by conftest.py


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
    # Try to parse as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # If not JSON, it might be a validation error message
        # Return as error response
        return {"status": "error", "error_code": "INVALID_ARGUMENTS", "message": text}


async def _select_fragment_template(
    session: ClientSession, required_parameter: str = "text"
) -> tuple[str, str]:
    """Find a template/fragment pair whose schema includes a specific parameter."""
    list_result = await session.call_tool("list_templates", arguments={})
    list_response = _parse_json_response(list_result)

    if list_response.get("status") == "error":
        pytest.skip(f"Failed to list templates: {list_response.get('message')}")

    templates = list_response.get("data", {}).get("templates", [])

    if not templates:
        pytest.skip("No templates available")

    # Track what we've seen for better error messages
    checked = []

    for template in templates:
        template_id = template["template_id"]
        frag_list_result = await session.call_tool(
            "list_template_fragments", arguments={"template_id": template_id}
        )
        frag_list_response = _parse_json_response(frag_list_result)

        if frag_list_response.get("status") == "error":
            checked.append(f"{template_id}: error - {frag_list_response.get('message')}")
            continue

        fragments = frag_list_response.get("data", {}).get("fragments", [])

        for fragment in fragments:
            fragment_id = fragment.get("fragment_id")
            parameters = fragment.get("parameters", [])
            param_names = [param.get("name") for param in parameters]

            if any(param.get("name") == required_parameter for param in parameters):
                return template_id, fragment_id

            checked.append(f"{template_id}.{fragment_id}: has {param_names}")

    # Provide detailed skip message
    details = "\n  ".join(checked)
    pytest.skip(f"No fragments with '{required_parameter}' parameter found.\nChecked:\n  {details}")


async def _create_session_for_template(session: ClientSession, template_id: str) -> str:
    """Create a document session for a template and return its ID."""
    create_result = await session.call_tool(
        "create_document_session", arguments={"template_id": template_id}
    )
    create_response = _parse_json_response(create_result)
    assert create_response["status"] == "success"
    return create_response["data"]["session_id"]


@pytest.fixture
def logger() -> Logger:
    """Provide logger for tests."""
    return session_logger


# ============================================================================
# Tests: add_fragment
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_fragment_tool_exists(mcp_headers):
    """Verify add_fragment tool is registered."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            assert "add_fragment" in tool_names


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_fragment_requires_session_id(logger, mcp_headers):
    """Verify add_fragment requires session_id parameter."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "add_fragment",
                arguments={
                    "fragment_id": "paragraph",
                    "parameters": {"text": "Test"},
                },
            )
            response = _parse_json_response(result)
            assert response["status"] == "error"
            assert response["error_code"] == "INVALID_ARGUMENTS"


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_fragment_requires_fragment_id(logger, mcp_headers):
    """Verify add_fragment requires fragment_id parameter."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "add_fragment",
                arguments={
                    "session_id": "invalid-session",
                    "parameters": {"text": "Test"},
                },
            )
            response = _parse_json_response(result)
            assert response["status"] == "error"
            assert response["error_code"] == "INVALID_ARGUMENTS"


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_fragment_requires_parameters(logger, mcp_headers):
    """Verify add_fragment requires parameters argument."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "add_fragment",
                arguments={
                    "session_id": "test-session",
                    "fragment_id": "paragraph",
                },
            )
            response = _parse_json_response(result)
            assert response["status"] == "error"
            assert response["error_code"] == "INVALID_ARGUMENTS"


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_fragment_invalid_session(logger, mcp_headers):
    """Verify add_fragment handles non-existent session."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "add_fragment",
                arguments={
                    "session_id": "nonexistent-session-id",
                    "fragment_id": "paragraph",
                    "parameters": {"text": "Test"},
                },
            )
            response = _parse_json_response(result)
            assert response["status"] == "error"
            # Security: non-existent sessions return SESSION_NOT_FOUND (not INVALID_OPERATION)
            assert response["error_code"] in ["SESSION_NOT_FOUND", "INVALID_OPERATION"]
            assert (
                "session" in response["message"].lower()
                or "not found" in response["message"].lower()
            )


# ============================================================================
# Tests: list_session_fragments
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_list_session_fragments_tool_exists(mcp_headers):
    """Verify list_session_fragments tool is registered."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            assert "list_session_fragments" in tool_names


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_list_session_fragments_requires_session_id(logger, mcp_headers):
    """Verify list_session_fragments requires session_id parameter."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("list_session_fragments", arguments={})
            response = _parse_json_response(result)
            assert response["status"] == "error"
            assert response["error_code"] == "INVALID_ARGUMENTS"


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_list_session_fragments_invalid_session(logger, mcp_headers):
    """Verify list_session_fragments handles non-existent session."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "list_session_fragments",
                arguments={"session_id": "nonexistent-session"},
            )
            response = _parse_json_response(result)
            assert response["status"] == "error"
            # Security: non-existent sessions return SESSION_NOT_FOUND
            assert response["error_code"] in ["SESSION_NOT_FOUND", "INVALID_OPERATION"]


# ============================================================================
# Tests: remove_fragment
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_remove_fragment_tool_exists(mcp_headers):
    """Verify remove_fragment tool is registered."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            assert "remove_fragment" in tool_names


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_remove_fragment_requires_session_id(logger, mcp_headers):
    """Verify remove_fragment requires session_id parameter."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "remove_fragment",
                arguments={"fragment_instance_guid": "test-guid"},
            )
            response = _parse_json_response(result)
            assert response["status"] == "error"
            assert response["error_code"] == "INVALID_ARGUMENTS"


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_remove_fragment_requires_guid(logger, mcp_headers):
    """Verify remove_fragment requires fragment_instance_guid parameter."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "remove_fragment",
                arguments={"session_id": "test-session"},
            )
            response = _parse_json_response(result)
            assert response["status"] == "error"
            assert response["error_code"] == "INVALID_ARGUMENTS"


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_remove_fragment_invalid_session(logger, mcp_headers):
    """Verify remove_fragment handles non-existent session."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "remove_fragment",
                arguments={
                    "session_id": "nonexistent-session",
                    "fragment_instance_guid": "test-guid",
                },
            )
            response = _parse_json_response(result)
            assert response["status"] == "error"
            # Security: non-existent sessions return SESSION_NOT_FOUND
            assert response["error_code"] in ["SESSION_NOT_FOUND", "INVALID_OPERATION"]


# ============================================================================
# Tests: Fragment Management Workflow
# ============================================================================
