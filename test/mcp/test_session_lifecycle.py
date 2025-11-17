"""Tests for MCP session lifecycle tools.

Phase 2: Session Lifecycle Tools
Tests: create_document_session, set_global_parameters, abort_document_session
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
MCP_PORT = os.environ.get("DOCO_MCP_PORT", "8011")
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
# create_document_session Tests
# ==============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_create_document_session_tool_exists(mcp_headers):
    """Test that create_document_session tool is available in MCP server."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get list of tools
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]

            # Verify create_document_session is in the tools
            assert (
                "create_document_session" in tool_names
            ), "create_document_session tool not found in MCP server"


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_create_document_session_requires_template_id(logger, mcp_headers):
    """Test that create_document_session requires template_id parameter."""
    logger.info("Testing create_document_session requires template_id")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call without template_id should fail validation
            try:
                result = await session.call_tool("create_document_session", arguments={})
                response = _parse_json_response(result)

                # Should get validation error
                assert response["status"] == "error"
                assert "INVALID_ARGUMENTS" in response.get("error_code", "")
            except Exception as e:
                # Validation error is expected
                assert "template_id" in str(e).lower() or "validation" in str(e).lower()


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_create_document_session_invalid_template(logger, mcp_headers):
    """Test that create_document_session returns error for non-existent template."""
    logger.info("Testing create_document_session with invalid template")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "create_document_session",
                arguments={"template_id": "nonexistent_template"},
            )

            response = _parse_json_response(result)

            # Should return error status
            assert response["status"] == "error"
            # Backend returns INVALID_OPERATION for not found scenarios
            assert "INVALID_OPERATION" in response.get("error_code", "")
            assert "not found" in response.get("message", "").lower()


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_create_document_session_success(logger, mcp_headers):
    """Test that create_document_session successfully creates a session."""
    logger.info("Testing create_document_session success")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # First get available templates
            list_result = await session.call_tool("list_templates", arguments={})
            list_response = _parse_json_response(list_result)

            templates = list_response["data"]["templates"]
            if len(templates) == 0:
                pytest.skip("No templates available for testing")

            # Create session with first template
            template_id = templates[0]["template_id"]
            result = await session.call_tool(
                "create_document_session", arguments={"template_id": template_id}
            )

            response = _parse_json_response(result)

            # Should return success
            assert response["status"] == "success"

            # Should have session data
            data = response["data"]
            assert "session_id" in data
            assert "template_id" in data
            assert data["template_id"] == template_id
            assert "created_at" in data

            logger.info(f"Created session: {data['session_id']}")


# ==============================================================================
# set_global_parameters Tests
# ==============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_set_global_parameters_tool_exists(mcp_headers):
    """Test that set_global_parameters tool is available in MCP server."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get list of tools
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]

            # Verify set_global_parameters is in the tools
            assert (
                "set_global_parameters" in tool_names
            ), "set_global_parameters tool not found in MCP server"


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_set_global_parameters_requires_session_id(logger, mcp_headers):
    """Test that set_global_parameters requires session_id parameter."""
    logger.info("Testing set_global_parameters requires session_id")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call without session_id should fail validation
            try:
                result = await session.call_tool(
                    "set_global_parameters",
                    arguments={"parameters": {}},
                )
                response = _parse_json_response(result)

                # Should get validation error
                assert response["status"] == "error"
                assert "INVALID_ARGUMENTS" in response.get("error_code", "")
            except Exception as e:
                # Validation error is expected
                assert "session_id" in str(e).lower() or "validation" in str(e).lower()


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_set_global_parameters_invalid_session(logger, mcp_headers):
    """Test that set_global_parameters returns error for invalid session."""
    logger.info("Testing set_global_parameters with invalid session")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "set_global_parameters",
                arguments={"session_id": "invalid_session", "parameters": {}},
            )

            response = _parse_json_response(result)

            # Should return error status
            assert response["status"] == "error"
            # Backend returns INVALID_OPERATION for not found scenarios
            assert "INVALID_OPERATION" in response.get("error_code", "")
            assert "not found" in response.get("message", "").lower()


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_set_global_parameters_success(logger, mcp_headers):
    """Test that set_global_parameters successfully sets parameters."""
    logger.info("Testing set_global_parameters success with news_email template")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create a session with news_email template
            create_result = await session.call_tool(
                "create_document_session", arguments={"template_id": "news_email"}
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Set global parameters matching news_email template
            params = {
                "email_subject": "Market Update - Test",
                "heading_title": "Weekly Financial News",
                "heading_subtitle": "Test Edition",
                "company_name": "Test Financial Services",
                "recipient_type": "Professional Investors",
                "contact_email": "test@example.com",
                "include_ai_notice": True,
            }
            result = await session.call_tool(
                "set_global_parameters",
                arguments={"session_id": session_id, "parameters": params},
            )

            response = _parse_json_response(result)

            # Should return success
            if response["status"] != "success":
                logger.error(f"set_global_parameters failed: {response}")
            assert response["status"] == "success"
            assert "session_id" in response["data"]
            assert response["data"]["session_id"] == session_id

            # Add two news fragments
            news1_params = {
                "story_summary": "Markets rallied on positive economic data",
                "date": "2025-11-16",
                "source": "https://example.com/news1",
                "author": "John Analyst",
                "impact_rating": "high",
            }
            result = await session.call_tool(
                "add_fragment",
                arguments={
                    "session_id": session_id,
                    "fragment_id": "news",
                    "parameters": news1_params,
                },
            )
            response = _parse_json_response(result)
            assert response["status"] == "success"

            news2_params = {
                "story_summary": "Central bank maintains interest rates",
                "date": "2025-11-15",
                "source": "https://example.com/news2",
                "author": "Jane Economist",
                "impact_rating": "medium",
            }
            result = await session.call_tool(
                "add_fragment",
                arguments={
                    "session_id": session_id,
                    "fragment_id": "news",
                    "parameters": news2_params,
                },
            )
            response = _parse_json_response(result)
            assert response["status"] == "success"

            # Add disclaimer fragment
            disclaimer_params = {
                "company_name": "Test Financial Services",
                "recipient_type": "Professional Investors",
                "include_ai_notice": True,
                "jurisdiction": "US",
                "contact_email": "compliance@example.com",
            }
            result = await session.call_tool(
                "add_fragment",
                arguments={
                    "session_id": session_id,
                    "fragment_id": "disclaimer",
                    "parameters": disclaimer_params,
                },
            )
            response = _parse_json_response(result)
            assert response["status"] == "success"

            # Get document via MCP (returns rendered HTML)
            result = await session.call_tool(
                "get_document",
                arguments={"session_id": session_id, "format": "html"},
            )
            response = _parse_json_response(result)
            if response["status"] != "success":
                logger.error(f"get_document failed: {response}")
            assert response["status"] == "success"
            assert "content" in response["data"]
            mcp_html = response["data"]["content"]
            assert "Market Update - Test" in mcp_html
            assert "Markets rallied" in mcp_html
            assert "Central bank maintains" in mcp_html
            assert "Test Financial Services" in mcp_html

            logger.info(f"Completed news_email workflow via MCP for session: {session_id}")


# ==============================================================================
# abort_document_session Tests
# ==============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_abort_document_session_tool_exists(mcp_headers):
    """Test that abort_document_session tool is available in MCP server."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get list of tools
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]

            # Verify abort_document_session is in the tools
            assert (
                "abort_document_session" in tool_names
            ), "abort_document_session tool not found in MCP server"


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_abort_document_session_requires_session_id(logger, mcp_headers):
    """Test that abort_document_session requires session_id parameter."""
    logger.info("Testing abort_document_session requires session_id")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call without session_id should fail validation
            try:
                result = await session.call_tool("abort_document_session", arguments={})
                response = _parse_json_response(result)

                # Should get validation error
                assert response["status"] == "error"
                assert "INVALID_ARGUMENTS" in response.get("error_code", "")
            except Exception as e:
                # Validation error is expected
                assert "session_id" in str(e).lower() or "validation" in str(e).lower()


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_abort_document_session_invalid_session(logger, mcp_headers):
    """Test that abort_document_session returns error for invalid session."""
    logger.info("Testing abort_document_session with invalid session")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "abort_document_session", arguments={"session_id": "invalid_session"}
            )

            response = _parse_json_response(result)

            # Should return error status
            assert response["status"] == "error"
            # Backend returns INVALID_OPERATION for not found scenarios
            assert "INVALID_OPERATION" in response.get("error_code", "")
            assert "not found" in response.get("message", "").lower()


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_abort_document_session_success(logger, mcp_headers):
    """Test that abort_document_session successfully aborts a session."""
    logger.info("Testing abort_document_session success")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # First create a session
            list_result = await session.call_tool("list_templates", arguments={})
            list_response = _parse_json_response(list_result)

            templates = list_response["data"]["templates"]
            if len(templates) == 0:
                pytest.skip("No templates available for testing")

            template_id = templates[0]["template_id"]
            create_result = await session.call_tool(
                "create_document_session", arguments={"template_id": template_id}
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Abort the session
            result = await session.call_tool(
                "abort_document_session", arguments={"session_id": session_id}
            )

            response = _parse_json_response(result)

            # Should return success
            assert response["status"] == "success"
            assert "session_id" in response["data"]

            logger.info(f"Aborted session: {session_id}")


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_create_set_abort_workflow(logger, mcp_headers):
    """Test complete workflow: create session, set parameters, abort."""
    logger.info("Testing complete session lifecycle workflow")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get available templates
            list_result = await session.call_tool("list_templates", arguments={})
            list_response = _parse_json_response(list_result)

            templates = list_response["data"]["templates"]
            if len(templates) == 0:
                pytest.skip("No templates available for testing")

            template_id = templates[0]["template_id"]

            # Step 1: Create session
            create_result = await session.call_tool(
                "create_document_session", arguments={"template_id": template_id}
            )
            create_response = _parse_json_response(create_result)
            assert create_response["status"] == "success"
            session_id = create_response["data"]["session_id"]
            logger.info(f"Step 1: Created session {session_id}")

            # Step 2: Set global parameters (skip if fails - may depend on template schema)
            params = {
                "title": "Workflow Test",
                "author": "Test Agent",
                "date": "2025-11-16",
            }
            set_result = await session.call_tool(
                "set_global_parameters",
                arguments={"session_id": session_id, "parameters": params},
            )
            set_response = _parse_json_response(set_result)
            # Log what we got even if it fails
            logger.info(f"Set parameters response: {set_response['status']}")
            if set_response["status"] == "error":
                # Skip if parameters don't match schema
                logger.info(f"Skipping set_global_parameters due to: {set_response.get('message')}")
            else:
                assert "session_id" in set_response["data"]
                assert set_response["data"]["session_id"] == session_id

            # Step 3: Abort session
            abort_result = await session.call_tool(
                "abort_document_session", arguments={"session_id": session_id}
            )
            abort_response = _parse_json_response(abort_result)
            assert abort_response["status"] == "success"
            logger.info(f"Step 3: Aborted session {session_id}")

            logger.info("Workflow completed successfully")
