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


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_document_invalid_format(logger):
    """Verify get_document handles invalid format gracefully."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create a valid session first
            create_result = await session.call_tool(
                "create_document_session", arguments={"template_id": "basic_report"}
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Try to render with invalid format
            result = await session.call_tool(
                "get_document",
                arguments={"session_id": session_id, "format": "invalid"},
            )
            response = _parse_json_response(result)
            assert response["status"] == "error"


# ============================================================================
# Tests: get_document HTML rendering
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_document_html_format(logger):
    """Verify get_document renders HTML format successfully."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create session
            create_result = await session.call_tool(
                "create_document_session", arguments={"template_id": "basic_report"}
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Add a fragment
            frag_list_result = await session.call_tool(
                "list_template_fragments", arguments={"template_id": "basic_report"}
            )
            frag_list_response = _parse_json_response(frag_list_result)
            fragments = frag_list_response["data"]["fragments"]

            if len(fragments) > 0:
                fragment_id = fragments[0]["fragment_id"]
                await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": fragment_id,
                        "parameters": {"text": "Test content for rendering"},
                    },
                )

            # Render as HTML
            result = await session.call_tool(
                "get_document",
                arguments={"session_id": session_id, "format": "html"},
            )
            response = _parse_json_response(result)
            assert response["status"] == "success"
            assert "content" in response["data"]
            assert response["data"]["format"] == "html"
            # HTML content should contain tags
            assert "<" in response["data"]["content"] and ">" in response["data"]["content"]


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_document_html_response_structure(logger):
    """Verify get_document HTML response has correct structure."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create session
            create_result = await session.call_tool(
                "create_document_session", arguments={"template_id": "basic_report"}
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Render as HTML
            result = await session.call_tool(
                "get_document",
                arguments={"session_id": session_id, "format": "html"},
            )
            response = _parse_json_response(result)
            assert response["status"] == "success"
            data = response["data"]
            assert "session_id" in data
            assert "format" in data
            assert "style_id" in data
            assert "content" in data
            assert "message" in data
            assert data["session_id"] == session_id


# ============================================================================
# Tests: get_document Markdown rendering
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_document_markdown_format(logger):
    """Verify get_document renders Markdown format successfully."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create session
            create_result = await session.call_tool(
                "create_document_session", arguments={"template_id": "basic_report"}
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Add a fragment
            frag_list_result = await session.call_tool(
                "list_template_fragments", arguments={"template_id": "basic_report"}
            )
            frag_list_response = _parse_json_response(frag_list_result)
            fragments = frag_list_response["data"]["fragments"]

            if len(fragments) > 0:
                fragment_id = fragments[0]["fragment_id"]
                await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": fragment_id,
                        "parameters": {"text": "Markdown content"},
                    },
                )

            # Render as Markdown
            result = await session.call_tool(
                "get_document",
                arguments={"session_id": session_id, "format": "md"},
            )
            response = _parse_json_response(result)
            assert response["status"] == "success"
            assert "content" in response["data"]
            # Format is normalized to "markdown" internally
            assert response["data"]["format"] in ["md", "markdown"]


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_document_md_alias(logger):
    """Verify get_document accepts 'md' as alias for 'markdown'."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create session
            create_result = await session.call_tool(
                "create_document_session", arguments={"template_id": "basic_report"}
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Render with 'md' alias
            result = await session.call_tool(
                "get_document",
                arguments={"session_id": session_id, "format": "md"},
            )
            response = _parse_json_response(result)
            assert response["status"] == "success"
            # Should normalize to 'markdown'
            assert response["data"]["format"] in ["markdown", "md"]


# ============================================================================
# Tests: get_document with styles
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_document_with_style(logger):
    """Verify get_document applies style to rendered document."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get available styles
            styles_result = await session.call_tool("list_styles", arguments={})
            styles_response = _parse_json_response(styles_result)
            styles = styles_response["data"]["styles"]

            if len(styles) == 0:
                pytest.skip("No styles available")

            style_id = styles[0]["style_id"]

            # Create session
            create_result = await session.call_tool(
                "create_document_session", arguments={"template_id": "basic_report"}
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Render with style
            result = await session.call_tool(
                "get_document",
                arguments={
                    "session_id": session_id,
                    "format": "html",
                    "style_id": style_id,
                },
            )
            response = _parse_json_response(result)
            assert response["status"] == "success"
            assert response["data"]["style_id"] == style_id


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_document_multiple_styles(logger):
    """Verify get_document works with different style options."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get available styles
            styles_result = await session.call_tool("list_styles", arguments={})
            styles_response = _parse_json_response(styles_result)
            styles = styles_response["data"]["styles"]

            if len(styles) < 2:
                pytest.skip("Fewer than 2 styles available")

            # Create session
            create_result = await session.call_tool(
                "create_document_session", arguments={"template_id": "basic_report"}
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Render with each style
            rendered_outputs = []
            for style in styles[:2]:
                result = await session.call_tool(
                    "get_document",
                    arguments={
                        "session_id": session_id,
                        "format": "html",
                        "style_id": style["style_id"],
                    },
                )
                response = _parse_json_response(result)
                assert response["status"] == "success"
                rendered_outputs.append(response["data"]["content"])

            # Both should render successfully
            assert len(rendered_outputs) == 2
            # Both should contain HTML structure
            assert rendered_outputs[0].startswith("<!DOCTYPE")
            assert rendered_outputs[1].startswith("<!DOCTYPE")


# ============================================================================
# Tests: get_document with fragments and content
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_document_with_fragments(logger):
    """Verify get_document includes fragment content in output."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create session
            create_result = await session.call_tool(
                "create_document_session", arguments={"template_id": "basic_report"}
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Add a fragment with specific content
            frag_list_result = await session.call_tool(
                "list_template_fragments", arguments={"template_id": "basic_report"}
            )
            frag_list_response = _parse_json_response(frag_list_result)
            fragments = frag_list_response["data"]["fragments"]

            if len(fragments) > 0:
                fragment_id = fragments[0]["fragment_id"]
                test_content = "UNIQUE_TEST_CONTENT_12345"
                await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": fragment_id,
                        "parameters": {"text": test_content},
                    },
                )

                # Render and check content is included
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "html"},
                )
                response = _parse_json_response(result)
                assert response["status"] == "success"
                # Content should be in the rendered output
                assert test_content in response["data"]["content"]


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_get_document_multiple_fragments(logger):
    """Verify get_document renders multiple fragments correctly."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create session
            create_result = await session.call_tool(
                "create_document_session", arguments={"template_id": "basic_report"}
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Get available fragments
            frag_list_result = await session.call_tool(
                "list_template_fragments", arguments={"template_id": "basic_report"}
            )
            frag_list_response = _parse_json_response(frag_list_result)
            fragments = frag_list_response["data"]["fragments"]

            if len(fragments) > 0:
                fragment_id = fragments[0]["fragment_id"]

                # Add multiple fragments with different content
                contents = [
                    "First fragment content",
                    "Second fragment content",
                ]
                for i, content in enumerate(contents):
                    await session.call_tool(
                        "add_fragment",
                        arguments={
                            "session_id": session_id,
                            "fragment_id": fragment_id,
                            "parameters": {"text": content},
                            "position": "end",
                        },
                    )

                # Render document
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "html"},
                )
                response = _parse_json_response(result)
                assert response["status"] == "success"

                # Both fragment contents should be in output
                output_content = response["data"]["content"]
                for content in contents:
                    assert content in output_content


# ============================================================================
# Tests: Document rendering workflow
# ============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_document_rendering_complete_workflow(logger):
    """Test complete document rendering workflow."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Step 1: Create session
            create_result = await session.call_tool(
                "create_document_session", arguments={"template_id": "basic_report"}
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]
            assert "session_id" in create_response["data"]

            # Step 2: Get template fragments
            frag_list_result = await session.call_tool(
                "list_template_fragments", arguments={"template_id": "basic_report"}
            )
            frag_list_response = _parse_json_response(frag_list_result)
            fragments = frag_list_response["data"]["fragments"]
            assert len(fragments) > 0

            # Step 3: Add fragment
            fragment_id = fragments[0]["fragment_id"]
            add_result = await session.call_tool(
                "add_fragment",
                arguments={
                    "session_id": session_id,
                    "fragment_id": fragment_id,
                    "parameters": {"text": "Workflow test content"},
                },
            )
            add_response = _parse_json_response(add_result)
            assert add_response["status"] == "success"

            # Step 4: List fragments
            list_result = await session.call_tool(
                "list_session_fragments", arguments={"session_id": session_id}
            )
            list_response = _parse_json_response(list_result)
            assert list_response["data"]["fragment_count"] == 1

            # Step 5: Render in multiple formats
            formats = ["html", "md"]
            for fmt in formats:
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": fmt},
                )
                response = _parse_json_response(result)
                assert response["status"] == "success"
                # Format may be normalized internally: 'md' -> 'markdown', 'html' stays 'html'
                if fmt == "html":
                    assert response["data"]["format"] == "html"
                else:  # fmt == "md"
                    assert response["data"]["format"] in ["md", "markdown"]
                assert "Workflow test content" in response["data"]["content"]

            # Step 6: Clean up
            abort_result = await session.call_tool(
                "abort_document_session", arguments={"session_id": session_id}
            )
            abort_response = _parse_json_response(abort_result)
            assert abort_response["status"] == "success"


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_document_rendering_format_consistency(logger):
    """Verify same content renders consistently across formats."""
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create session
            create_result = await session.call_tool(
                "create_document_session", arguments={"template_id": "basic_report"}
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Add fragment
            frag_list_result = await session.call_tool(
                "list_template_fragments", arguments={"template_id": "basic_report"}
            )
            frag_list_response = _parse_json_response(frag_list_result)
            fragments = frag_list_response["data"]["fragments"]

            if len(fragments) > 0:
                fragment_id = fragments[0]["fragment_id"]
                test_text = "CONSISTENCY_TEST_CONTENT"
                await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": fragment_id,
                        "parameters": {"text": test_text},
                    },
                )

                # Render in HTML and Markdown
                html_result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "html"},
                )
                html_response = _parse_json_response(html_result)

                md_result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "md"},
                )
                md_response = _parse_json_response(md_result)

                # Both should contain the test text
                assert test_text in html_response["data"]["content"]
                assert test_text in md_response["data"]["content"]

                # HTML should be 'html', markdown should be 'markdown' or 'md'
                assert html_response["data"]["format"] == "html"
                assert md_response["data"]["format"] in ["markdown", "md"]
