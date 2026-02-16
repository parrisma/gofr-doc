"""Fragment management integration tests for MCP server.

Tests cover:
  - add_fragment: Adding fragment instances to document sessions
  - remove_fragment: Removing fragment instances from sessions
  - list_session_fragments: Listing fragments currently in a session
"""

import json
import os
import uuid
from typing import Any, Dict

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent

from app.logger import Logger, session_logger

# MCP server configuration via environment variables (defaults to production port)
MCP_HOST = os.environ.get("GOFR_DOC_MCP_HOST", "localhost")
MCP_PORT = os.environ.get("GOFR_DOC_MCP_PORT", "8040")
MCP_URL = f"http://{MCP_HOST}:{MCP_PORT}/mcp/"

# Note: auth_service and server_mcp_headers fixtures are now provided by conftest.py


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
    unique_alias = f"test-fragment-mgmt-{uuid.uuid4().hex[:8]}"
    create_result = await session.call_tool(
        "create_document_session",
        arguments={"template_id": template_id, "alias": unique_alias},
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
async def test_add_fragment_tool_exists(server_mcp_headers):
    """Verify add_fragment tool is registered."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            assert "add_fragment" in tool_names


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_fragment_requires_session_id(logger, server_mcp_headers):
    """Verify add_fragment requires session_id parameter."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
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
async def test_add_fragment_requires_fragment_id(logger, server_mcp_headers):
    """Verify add_fragment requires fragment_id parameter."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
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
async def test_add_fragment_requires_parameters(logger, server_mcp_headers):
    """Verify add_fragment requires parameters argument."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
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
async def test_add_fragment_invalid_session(logger, server_mcp_headers):
    """Verify add_fragment handles non-existent session."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
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
async def test_list_session_fragments_tool_exists(server_mcp_headers):
    """Verify list_session_fragments tool is registered."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            assert "list_session_fragments" in tool_names


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_list_session_fragments_requires_session_id(logger, server_mcp_headers):
    """Verify list_session_fragments requires session_id parameter."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool("list_session_fragments", arguments={})
            response = _parse_json_response(result)
            assert response["status"] == "error"
            assert response["error_code"] == "INVALID_ARGUMENTS"


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_list_session_fragments_invalid_session(logger, server_mcp_headers):
    """Verify list_session_fragments handles non-existent session."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
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
async def test_remove_fragment_tool_exists(server_mcp_headers):
    """Verify remove_fragment tool is registered."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            assert "remove_fragment" in tool_names


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_remove_fragment_requires_session_id(logger, server_mcp_headers):
    """Verify remove_fragment requires session_id parameter."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
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
async def test_remove_fragment_requires_guid(logger, server_mcp_headers):
    """Verify remove_fragment requires fragment_instance_guid parameter."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
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
async def test_remove_fragment_invalid_session(logger, server_mcp_headers):
    """Verify remove_fragment handles non-existent session."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
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


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_table_fragment_with_column_widths(logger, server_mcp_headers):
    """Test adding a table fragment with column_widths parameter (Phase 6)."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create session with basic_report template (has table fragment)
            session_id = await _create_session_for_template(session, "basic_report")
            logger.info(f"Created session: {session_id}")

            # Add table fragment with column_widths
            add_result = await session.call_tool(
                "add_fragment",
                arguments={
                    "session_id": session_id,
                    "fragment_id": "table",
                    "parameters": {
                        "rows": [
                            ["Product", "Price", "Stock"],
                            ["Widget", "$9.99", "150"],
                            ["Gadget", "$19.99", "75"],
                        ],
                        "has_header": True,
                        "column_widths": {"0": "40%", "1": "30%", "2": "30%"},
                    },
                },
            )
            add_response = _parse_json_response(add_result)
            logger.info(f"Add fragment response: {add_response.get('status')}")

            assert add_response["status"] == "success"
            assert "fragment_instance_guid" in add_response["data"]

            # Verify fragment was added with column_widths
            list_result = await session.call_tool(
                "list_session_fragments", arguments={"session_id": session_id}
            )
            list_response = _parse_json_response(list_result)
            assert list_response["status"] == "success"
            fragments = list_response["data"]["fragments"]
            assert len(fragments) == 1

            fragment = fragments[0]
            assert fragment["fragment_id"] == "table"
            assert "column_widths" in fragment["parameters"]
            assert fragment["parameters"]["column_widths"] == {"0": "40%", "1": "30%", "2": "30%"}


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_table_fragment_with_invalid_column_widths(logger, server_mcp_headers):
    """Test adding table with invalid column_widths (exceeds 100%)."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            session_id = await _create_session_for_template(session, "basic_report")
            logger.info(f"Created session: {session_id}")

            # Try to add table with column_widths totaling > 100%
            add_result = await session.call_tool(
                "add_fragment",
                arguments={
                    "session_id": session_id,
                    "fragment_id": "table",
                    "parameters": {
                        "rows": [["A", "B"], ["1", "2"]],
                        "has_header": False,
                        "column_widths": {"0": "60%", "1": "50%"},  # Total: 110%
                    },
                },
            )
            add_response = _parse_json_response(add_result)
            logger.info(f"Response: {add_response}")

            # Should fail validation
            assert add_response["status"] == "error"
            assert (
                "100%" in add_response.get("message", "").lower()
                or "exceed" in add_response.get("message", "").lower()
            )


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_table_fragment_with_all_phase6_features(logger, server_mcp_headers):
    """Test table fragment with all Phase 1-6 parameters combined."""
    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            session_id = await _create_session_for_template(session, "basic_report")

            # Add comprehensive table with all features
            add_result = await session.call_tool(
                "add_fragment",
                arguments={
                    "session_id": session_id,
                    "fragment_id": "table",
                    "parameters": {
                        "rows": [
                            ["Product", "Price", "Quantity", "Total"],
                            ["Widget", "9.99", "10", "99.90"],
                            ["Gadget", "19.99", "5", "99.95"],
                            ["Gizmo", "14.99", "8", "119.92"],
                        ],
                        "has_header": True,
                        "title": "Q4 Sales Report",
                        "width": "full",
                        "column_alignments": ["left", "right", "right", "right"],
                        "border_style": "full",
                        "zebra_stripe": True,
                        "compact": False,
                        "number_format": {"1": "currency:USD", "3": "currency:USD"},
                        "header_color": "primary",
                        "stripe_color": "light",
                        "highlight_columns": {"3": "success"},
                        "sort_by": {"column": 3, "order": "desc"},
                        "column_widths": {"0": "40%", "1": "20%", "2": "20%", "3": "20%"},
                    },
                },
            )
            add_response = _parse_json_response(add_result)

            assert add_response["status"] == "success"

            # Verify all parameters were saved
            list_result = await session.call_tool(
                "list_session_fragments", arguments={"session_id": session_id}
            )
            list_response = _parse_json_response(list_result)
            fragment = list_response["data"]["fragments"][0]
            params = fragment["parameters"]

            assert params["title"] == "Q4 Sales Report"
            assert params["column_widths"] == {"0": "40%", "1": "20%", "2": "20%", "3": "20%"}
            assert params["sort_by"] == {"column": 3, "order": "desc"}
            assert params["header_color"] == "primary"
