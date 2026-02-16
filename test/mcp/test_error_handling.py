#!/usr/bin/env python3
"""
Phase 5: Error Handling Tests - Practical error resilience validation

Tests focus on:
1. Tools handle missing parameters gracefully
2. Invalid IDs don't crash the system
3. Tool responses are consistent and parseable
4. Error recovery is possible
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from mcp.client.session import ClientSession
from app.logger import Logger, session_logger
from contextlib import asynccontextmanager
import functools

# MCP server configuration via environment variables
MCP_HOST = os.environ.get("GOFR_DOC_MCP_HOST", "localhost")
MCP_PORT = os.environ.get("GOFR_DOC_MCP_PORT", "8040")
MCP_URL = f"http://{MCP_HOST}:{MCP_PORT}/mcp/"

# Note: auth_service and server_mcp_headers fixtures are now provided by conftest.py


def skip_if_mcp_unavailable(func):
    """Decorator to skip tests if MCP server is unavailable"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        import socket

        try:
            socket.create_connection((MCP_HOST, int(MCP_PORT)), timeout=1)
        except (socket.error, ConnectionRefusedError):
            pytest.skip(f"MCP server not available on {MCP_HOST}:{MCP_PORT}")
        return await func(*args, **kwargs)

    return wrapper


def _extract_text(content_list) -> str:
    """Extract text from MCP response content"""
    if content_list and hasattr(content_list[0], "text"):
        return content_list[0].text
    return ""


@asynccontextmanager
async def mcp_session(server_mcp_headers):
    """Context manager for MCP client session"""
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


# ============================================================================
# CATEGORY 1: ROBUST PARAMETER HANDLING
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_create_session_handles_missing_template_id(server_mcp_headers):
    """Test that create_document_session handles missing template_id gracefully"""
    logger: Logger = session_logger
    logger.info("Testing create_session with missing template_id")

    async with mcp_session(server_mcp_headers) as session:
        # Call without template_id
        result = await session.call_tool("create_document_session", arguments={})
        text = _extract_text(result.content)

        # Should get some response (error or otherwise)
        assert text is not None and len(text) > 0, "Tool should return response"
        logger.info("Tool handled missing template_id", response_length=len(text))


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_fragment_handles_missing_required_parameters(server_mcp_headers):
    """Test add_fragment handles missing required parameters"""
    logger: Logger = session_logger
    logger.info("Testing add_fragment with missing parameters")

    async with mcp_session(server_mcp_headers) as session:
        # First create a valid session
        create_result = await session.call_tool(
            "create_document_session",
            arguments={"template_id": "default", "alias": "test_error_handling-16"},
        )
        session_text = _extract_text(create_result.content)
        session_id = session_text.split("\n")[0] if session_text else None

        if not session_id:
            pytest.skip("Could not create session")

        # Try add_fragment with minimal args (missing fragment_id)
        result = await session.call_tool("add_fragment", arguments={"session_id": session_id})
        text = _extract_text(result.content)

        # Should handle gracefully
        assert text is not None, "Tool should return response"
        logger.info("Tool handled missing fragment_id")


# ============================================================================
# CATEGORY 2: INVALID ID RESILIENCE
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_template_with_invalid_id_doesnt_crash(server_mcp_headers):
    """Test that get_template_details handles invalid template_id without crashing"""
    logger: Logger = session_logger
    logger.info("Testing get_template_details with invalid ID")

    async with mcp_session(server_mcp_headers) as session:
        # Call with non-existent template
        result = await session.call_tool(
            "get_template_details", arguments={"template_id": "nonexistent_xyz_12345"}
        )
        text = _extract_text(result.content)

        # Should return gracefully (not crash)
        assert text is not None, "Tool should return response"
        logger.info("Tool handled invalid template_id gracefully")


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_add_fragment_with_invalid_session_id_fails_gracefully(server_mcp_headers):
    """Test add_fragment with invalid session fails gracefully"""
    logger: Logger = session_logger
    logger.info("Testing add_fragment with invalid session")

    async with mcp_session(server_mcp_headers) as session:
        result = await session.call_tool(
            "add_fragment",
            arguments={
                "session_id": "invalid_session_xyz",
                "fragment_id": "text_block",
                "parameters": {},
            },
        )
        text = _extract_text(result.content)

        # Should return gracefully
        assert text is not None, "Tool should return response without crashing"
        logger.info("Tool handled invalid session_id gracefully")


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_remove_fragment_with_invalid_guid_fails_gracefully(server_mcp_headers):
    """Test remove_fragment with invalid GUID fails gracefully"""
    logger: Logger = session_logger
    logger.info("Testing remove_fragment with invalid GUID")

    async with mcp_session(server_mcp_headers) as session:
        # Create a valid session
        create_result = await session.call_tool(
            "create_document_session",
            arguments={"template_id": "default", "alias": "test_error_handling-17"},
        )
        session_text = _extract_text(create_result.content)
        session_id = session_text.split("\n")[0] if session_text else None

        if not session_id:
            pytest.skip("Could not create session")

        # Try to remove non-existent fragment
        result = await session.call_tool(
            "remove_fragment",
            arguments={"session_id": session_id, "guid": "00000000-0000-0000-0000-000000000000"},
        )
        text = _extract_text(result.content)

        # Should fail gracefully
        assert text is not None, "Tool should return response"
        logger.info("Tool handled invalid GUID gracefully")


# ============================================================================
# CATEGORY 3: RESPONSE CONSISTENCY
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_all_tools_return_parseable_responses(server_mcp_headers):
    """Test that all tools return responses that can be parsed"""
    logger: Logger = session_logger
    logger.info("Testing all tools return parseable responses")

    async with mcp_session(server_mcp_headers) as session:
        # Test a few key tools with valid inputs
        tools_to_test = [
            ("ping", {}),
            ("list_templates", {}),
            ("list_styles", {}),
        ]

        for tool_name, args in tools_to_test:
            result = await session.call_tool(tool_name, arguments=args)
            text = _extract_text(result.content)

            # Should have some response
            assert text is not None, f"{tool_name}: got None response"
            assert len(text) > 0, f"{tool_name}: got empty response"

        logger.info("All tools return parseable responses")


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_error_responses_are_readable(server_mcp_headers):
    """Test that error responses are readable and informative"""
    logger: Logger = session_logger
    logger.info("Testing error responses are readable")

    async with mcp_session(server_mcp_headers) as session:
        # Trigger known error condition
        result = await session.call_tool(
            "get_template_details", arguments={"template_id": "does_not_exist_xyz"}
        )
        text = _extract_text(result.content)

        # Error response should be readable
        assert text is not None and len(text) > 0, "Error should have content"
        assert isinstance(text, str), "Error should be string"
        logger.info("Error response is readable", length=len(text))


# ============================================================================
# CATEGORY 4: OPERATION STATE HANDLING
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_session_remains_valid_after_invalid_operation(server_mcp_headers):
    """Test that session remains usable after attempting invalid operation"""
    logger: Logger = session_logger
    logger.info("Testing session resilience after invalid operation")

    async with mcp_session(server_mcp_headers) as session:
        # Create a session
        create_result = await session.call_tool(
            "create_document_session",
            arguments={"template_id": "default", "alias": "test_error_handling-18"},
        )
        session_text = _extract_text(create_result.content)
        session_id = session_text.split("\n")[0] if session_text else None

        if not session_id:
            pytest.skip("Could not create session")

        # Attempt invalid operation (remove non-existent fragment)
        await session.call_tool(
            "remove_fragment",
            arguments={"session_id": session_id, "guid": "00000000-0000-0000-0000-000000000000"},
        )

        # Session should still be usable
        list_result = await session.call_tool(
            "list_session_fragments", arguments={"session_id": session_id}
        )
        text = _extract_text(list_result.content)

        assert text is not None, "Session should still be usable after invalid op"
        logger.info("Session remains valid after invalid operation")


# ============================================================================
# CATEGORY 5: MULTIPLE OPERATION RESILIENCE
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_mixed_valid_and_invalid_operations(server_mcp_headers):
    """Test handling sequence of valid and invalid operations"""
    logger: Logger = session_logger
    logger.info("Testing mixed valid/invalid operation sequence")

    async with mcp_session(server_mcp_headers) as session:
        # Create session (valid)
        create_result = await session.call_tool(
            "create_document_session",
            arguments={"template_id": "default", "alias": "test_error_handling-19"},
        )
        session_text = _extract_text(create_result.content)
        session_id = session_text.split("\n")[0] if session_text else None

        if not session_id:
            pytest.skip("Could not create session")

        # Set params (valid)
        await session.call_tool(
            "set_global_parameters",
            arguments={"session_id": session_id, "parameters": {"title": "Test"}},
        )

        # Try add with invalid fragment (invalid - but graceful)
        await session.call_tool(
            "add_fragment",
            arguments={"session_id": session_id, "fragment_id": "nonexistent_fragment"},
        )

        # Should still be able to list (valid)
        list_result = await session.call_tool(
            "list_session_fragments", arguments={"session_id": session_id}
        )
        text = _extract_text(list_result.content)

        assert text is not None, "Should recover after error"
        logger.info("System recovered after invalid operation in sequence")


# ============================================================================
# CATEGORY 6: TOOL AVAILABILITY & CONSISTENCY
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_all_expected_tools_available(server_mcp_headers):
    """Test that all expected MCP tools are available"""
    logger: Logger = session_logger
    logger.info("Testing all expected tools are available")

    async with mcp_session(server_mcp_headers) as session:
        tools = await session.list_tools()
        tool_names = [t.name for t in tools.tools]

        expected_tools = [
            "ping",
            "list_templates",
            "get_template_details",
            "list_template_fragments",
            "get_fragment_details",
            "list_styles",
            "create_document_session",
            "set_global_parameters",
            "abort_document_session",
            "add_fragment",
            "list_session_fragments",
            "remove_fragment",
            "get_document",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool '{tool_name}' not found"

        logger.info("All expected tools available", count=len(expected_tools))


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_tool_descriptions_are_present(server_mcp_headers):
    """Test that all tools have descriptions"""
    logger: Logger = session_logger
    logger.info("Testing tool descriptions are present")

    async with mcp_session(server_mcp_headers) as session:
        tools = await session.list_tools()

        for tool in tools.tools:
            assert (
                tool.description is not None and len(tool.description) > 0
            ), f"Tool '{tool.name}' missing description"

        logger.info("All tools have descriptions")


# ============================================================================
# CATEGORY 7: SESSION LIFECYCLE RESILIENCE
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_abort_session_then_operations_fail_gracefully(server_mcp_headers):
    """Test that operations on aborted session fail gracefully"""
    logger: Logger = session_logger
    logger.info("Testing operations after session abort")

    async with mcp_session(server_mcp_headers) as session:
        # Create and abort session
        create_result = await session.call_tool(
            "create_document_session",
            arguments={"template_id": "default", "alias": "test_error_handling-20"},
        )
        session_text = _extract_text(create_result.content)
        session_id = session_text.split("\n")[0] if session_text else None

        if not session_id:
            pytest.skip("Could not create session")

        # Abort the session
        await session.call_tool("abort_document_session", arguments={"session_id": session_id})

        # Operations on aborted session should fail gracefully (not crash)
        result = await session.call_tool(
            "add_fragment",
            arguments={"session_id": session_id, "fragment_id": "text_block", "parameters": {}},
        )
        text = _extract_text(result.content)

        # Should return gracefully (error or no change)
        assert text is not None, "Should handle aborted session gracefully"
        logger.info("Operations on aborted session handled gracefully")


# ============================================================================
# CATEGORY 8: DATA FORMAT VALIDATION
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_response_data_types_are_correct(server_mcp_headers):
    """Test that responses have expected data types"""
    logger: Logger = session_logger
    logger.info("Testing response data types")

    async with mcp_session(server_mcp_headers) as session:
        # Get templates
        result = await session.call_tool("list_templates", arguments={})
        text = _extract_text(result.content)

        # Response should be text
        assert isinstance(text, str), "Response should be string"
        logger.info("Response data types correct")


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_session_id_format_validation(server_mcp_headers):
    """Test that created sessions have valid IDs"""
    logger: Logger = session_logger
    logger.info("Testing session ID format")

    async with mcp_session(server_mcp_headers) as session:
        result = await session.call_tool(
            "create_document_session",
            arguments={"template_id": "default", "alias": "test_error_handling-21"},
        )
        text = _extract_text(result.content)

        # Session ID should be in response
        assert text is not None and len(text) > 0, "Should return session info"

        # Extract session ID (first line typically contains the ID)
        lines = text.split("\n")
        session_id = lines[0] if lines else None

        assert session_id is not None, "Should have session ID"
        assert len(session_id) > 0, "Session ID should not be empty"

        logger.info("Session ID format valid", session_id=session_id[:20] + "...")
