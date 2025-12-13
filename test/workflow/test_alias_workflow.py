#!/usr/bin/env python3
"""Integration tests demonstrating complete workflows using ONLY aliases (no GUIDs).

Phase 10: Alias Integration Tests

These tests prove that the entire document generation workflow can be completed
using friendly session aliases instead of UUIDs. After session creation, the
UUID returned is NEVER used - only the alias.

This validates the core goal: LLMs and users can work with memorable names
like 'q4-report' instead of '550e8400-e29b-41d4-a716-446655440000'.

Test Scenarios:
- 10.1: Basic alias-only workflow (create → params → fragments → render)
- 10.2: Discovery workflow (create multiple → list → use discovered aliases)
- 10.3: Iterative workflow (create → render → add more → re-render)
- 10.4: Multi-format workflow (render to HTML, PDF, MD using alias)
- 10.5: Error handling (non-existent alias → helpful errors)

Requires:
- MCP server running on port 8011 with JWT authentication
- Web server running on port 8010 with JWT authentication
"""

import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Port configuration - use test ports from environment
MCP_PORT = os.environ.get("GOFR_DOC_MCP_PORT", "8040")
WEB_PORT = os.environ.get("GOFR_DOC_WEB_PORT", "8012")
MCP_URL = f"http://127.0.0.1:{MCP_PORT}/mcp/"


def _extract_text(result):
    """Extract text content from MCP tool result."""
    if not result or not result.content:
        return ""
    for item in result.content:
        if isinstance(item, TextContent):
            return item.text
    return ""


def _parse_response(result):
    """Parse JSON response from MCP tool result."""
    text = _extract_text(result)
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


class TestAliasOnlyWorkflow:
    """Test complete workflows using ONLY aliases, never UUIDs."""

    @pytest.mark.asyncio
    async def test_basic_alias_only_workflow(self, mcp_headers):
        """Task 10.1: Complete document workflow using only the alias.

        This test demonstrates that after creating a session with an alias,
        all subsequent operations can use the alias instead of the UUID.
        The UUID is intentionally IGNORED after creation.

        Workflow:
        1. Create session with alias "quarterly-report"
        2. Set global parameters using alias (NOT UUID)
        3. Add fragment using alias (NOT UUID)
        4. List fragments using alias (NOT UUID)
        5. Render document using alias (NOT UUID)
        6. Abort session using alias (NOT UUID)

        Key assertion: UUID from create_document_session is never used!
        """

        # Use a unique alias for this test
        test_alias = "quarterly-report-basic"

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # ============================================================
                # Step 1: Create session with friendly alias
                # ============================================================
                result = await session.call_tool(
                    "create_document_session",
                    arguments={
                        "template_id": "basic_report",
                        "alias": test_alias,
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"Create failed: {response}"

                # We get a UUID back, but we're going to IGNORE it!
                returned_uuid = response.get("data", {}).get("session_id")
                returned_alias = response.get("data", {}).get("alias")

                assert returned_uuid, "No session_id returned"
                assert returned_alias == test_alias, f"Alias mismatch: {returned_alias}"

                # ============================================================
                # Step 2: Set global parameters using ALIAS (not UUID!)
                # ============================================================
                result = await session.call_tool(
                    "set_global_parameters",
                    arguments={
                        "session_id": test_alias,  # <-- Using ALIAS, not UUID!
                        "parameters": {
                            "title": "Q4 2025 Quarterly Report",
                            "author": "Integration Test Suite",
                        },
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"Set params failed: {response}"

                # ============================================================
                # Step 3: Add fragment using ALIAS (not UUID!)
                # ============================================================
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": test_alias,  # <-- Using ALIAS, not UUID!
                        "fragment_id": "paragraph",
                        "parameters": {
                            "text": "This report was generated using session aliases instead of UUIDs.",
                        },
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"Add fragment failed: {response}"
                fragment_guid = response.get("data", {}).get("fragment_instance_guid")
                assert fragment_guid, "No fragment GUID returned"

                # ============================================================
                # Step 4: List fragments using ALIAS (not UUID!)
                # ============================================================
                result = await session.call_tool(
                    "list_session_fragments",
                    arguments={
                        "session_id": test_alias,  # <-- Using ALIAS, not UUID!
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"List fragments failed: {response}"
                fragments = response.get("data", {}).get("fragments", [])
                assert len(fragments) == 1, f"Expected 1 fragment, got {len(fragments)}"

                # ============================================================
                # Step 5: Render document using ALIAS (not UUID!)
                # ============================================================
                result = await session.call_tool(
                    "get_document",
                    arguments={
                        "session_id": test_alias,  # <-- Using ALIAS, not UUID!
                        "format": "html",
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"Render failed: {response}"

                html_content = response.get("data", {}).get("content", "")
                assert len(html_content) > 100, "HTML content too short"
                assert "Q4 2025 Quarterly Report" in html_content, "Title not in HTML"
                assert "session aliases" in html_content, "Fragment text not in HTML"

                # ============================================================
                # Step 6: Get session status using ALIAS (not UUID!)
                # ============================================================
                result = await session.call_tool(
                    "get_session_status",
                    arguments={
                        "session_id": test_alias,  # <-- Using ALIAS, not UUID!
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"Get status failed: {response}"
                # Session should have global params set
                assert (
                    response.get("data", {}).get("has_global_parameters") is True
                ), "Session should have global params"

                # ============================================================
                # Step 7: Abort session using ALIAS (not UUID!)
                # ============================================================
                result = await session.call_tool(
                    "abort_document_session",
                    arguments={
                        "session_id": test_alias,  # <-- Using ALIAS, not UUID!
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"Abort failed: {response}"

                # ============================================================
                # Verification: The UUID was NEVER used after creation!
                # ============================================================
                # All 6 operations above used test_alias, not returned_uuid
                # This proves the alias system works end-to-end

    @pytest.mark.asyncio
    async def test_discovery_workflow_with_aliases(self, mcp_headers):
        """Task 10.2: Create multiple sessions, discover via list, use discovered aliases.

        This test demonstrates the discovery workflow:
        1. Create 3 sessions with different aliases
        2. Call list_active_sessions to discover them
        3. Verify all aliases appear in the list
        4. Use a discovered alias to render a document
        5. Clean up all sessions using aliases

        Key assertion: Aliases are discoverable and usable from list_active_sessions!
        """

        # Create 3 sessions with memorable aliases
        aliases = ["discovery-report-alpha", "discovery-report-beta", "discovery-report-gamma"]

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # ============================================================
                # Step 1: Create 3 sessions with different aliases
                # ============================================================
                for alias in aliases:
                    result = await session.call_tool(
                        "create_document_session",
                        arguments={
                            "template_id": "basic_report",
                            "alias": alias,
                        },
                    )
                    response = _parse_response(result)
                    assert response.get("status") == "success", f"Create {alias} failed: {response}"

                    # Set minimal params so session is usable
                    result = await session.call_tool(
                        "set_global_parameters",
                        arguments={
                            "session_id": alias,
                            "parameters": {"title": f"Report: {alias}"},
                        },
                    )
                    response = _parse_response(result)
                    assert response.get("status") == "success", f"Set params for {alias} failed"

                # ============================================================
                # Step 2: Discover sessions via list_active_sessions
                # ============================================================
                result = await session.call_tool(
                    "list_active_sessions",
                    arguments={},
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"List sessions failed: {response}"

                sessions_list = response.get("data", {}).get("sessions", [])
                session_count = response.get("data", {}).get("session_count", 0)

                # Should have at least our 3 sessions
                assert session_count >= 3, f"Expected at least 3 sessions, got {session_count}"

                # ============================================================
                # Step 3: Verify all our aliases appear in the list
                # ============================================================
                discovered_aliases = [s.get("alias") for s in sessions_list]

                for alias in aliases:
                    assert (
                        alias in discovered_aliases
                    ), f"Alias '{alias}' not found in list: {discovered_aliases}"

                # Verify each session has both session_id (UUID) and alias
                for s in sessions_list:
                    if s.get("alias") in aliases:
                        assert s.get("session_id"), f"Session missing session_id: {s}"
                        assert s.get("alias"), f"Session missing alias: {s}"
                        assert s.get("template_id") == "basic_report", f"Wrong template: {s}"

                # ============================================================
                # Step 4: Use a DISCOVERED alias to render a document
                # ============================================================
                # Pick the second alias from our list (beta)
                discovered_alias = aliases[1]  # "discovery-report-beta"

                # Add a fragment using the discovered alias
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": discovered_alias,  # Using discovered alias!
                        "fragment_id": "paragraph",
                        "parameters": {
                            "text": "This document was rendered using a discovered alias."
                        },
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"Add fragment failed: {response}"

                # Render using the discovered alias
                result = await session.call_tool(
                    "get_document",
                    arguments={
                        "session_id": discovered_alias,  # Using discovered alias!
                        "format": "html",
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"Render failed: {response}"

                html_content = response.get("data", {}).get("content", "")
                assert "discovered alias" in html_content, "Fragment text not in rendered HTML"
                assert (
                    "discovery-report-beta" in html_content
                    or "Report: discovery-report-beta" in html_content
                ), "Title not in HTML"

                # ============================================================
                # Step 5: Clean up all sessions using aliases
                # ============================================================
                for alias in aliases:
                    result = await session.call_tool(
                        "abort_document_session",
                        arguments={"session_id": alias},  # Using alias for cleanup!
                    )
                    response = _parse_response(result)
                    assert response.get("status") == "success", f"Abort {alias} failed: {response}"

                # Verify sessions are gone
                result = await session.call_tool(
                    "list_active_sessions",
                    arguments={},
                )
                response = _parse_response(result)
                remaining = response.get("data", {}).get("sessions", [])
                remaining_aliases = [s.get("alias") for s in remaining]

                for alias in aliases:
                    assert (
                        alias not in remaining_aliases
                    ), f"Alias '{alias}' should have been deleted"

    @pytest.mark.asyncio
    async def test_iterative_workflow_with_alias(self, mcp_headers):
        """Task 10.3: Create session, render, add more content, re-render using alias.

        This test demonstrates iterative document building:
        1. Create session with alias
        2. Add initial content and render (version 1)
        3. Add more fragments using alias
        4. Re-render using alias (version 2)
        5. Remove a fragment using alias
        6. Re-render using alias (version 3)
        7. Verify each version has expected content

        Key assertion: Alias works for iterative builds and re-renders!
        """

        test_alias = "iterative-report"

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # ============================================================
                # Step 1: Create session with alias
                # ============================================================
                result = await session.call_tool(
                    "create_document_session",
                    arguments={
                        "template_id": "basic_report",
                        "alias": test_alias,
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"Create failed: {response}"

                # Set global parameters
                result = await session.call_tool(
                    "set_global_parameters",
                    arguments={
                        "session_id": test_alias,
                        "parameters": {"title": "Iterative Document"},
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success"

                # ============================================================
                # Step 2: Add initial content and render (Version 1)
                # ============================================================
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": test_alias,
                        "fragment_id": "paragraph",
                        "parameters": {"text": "VERSION_ONE: Initial content."},
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success"
                first_fragment_guid = response.get("data", {}).get("fragment_instance_guid")

                # Render version 1
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": test_alias, "format": "html"},
                )
                response = _parse_response(result)
                assert response.get("status") == "success"
                html_v1 = response.get("data", {}).get("content", "")
                assert "VERSION_ONE" in html_v1, "Version 1 content missing"
                assert "VERSION_TWO" not in html_v1, "Version 2 content shouldn't exist yet"

                # ============================================================
                # Step 3: Add more fragments using alias
                # ============================================================
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": test_alias,
                        "fragment_id": "paragraph",
                        "parameters": {"text": "VERSION_TWO: Additional content added later."},
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success"
                # Store fragment GUID to verify it was created (used for logging/debugging)
                _ = response.get("data", {}).get("fragment_instance_guid")

                # ============================================================
                # Step 4: Re-render using alias (Version 2)
                # ============================================================
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": test_alias, "format": "html"},
                )
                response = _parse_response(result)
                assert response.get("status") == "success"
                html_v2 = response.get("data", {}).get("content", "")
                assert "VERSION_ONE" in html_v2, "Version 1 content should still exist"
                assert "VERSION_TWO" in html_v2, "Version 2 content missing"

                # Version 2 should be longer than version 1
                assert len(html_v2) > len(html_v1), "Version 2 should have more content"

                # ============================================================
                # Step 5: Remove first fragment using alias
                # ============================================================
                result = await session.call_tool(
                    "remove_fragment",
                    arguments={
                        "session_id": test_alias,
                        "fragment_instance_guid": first_fragment_guid,
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"Remove fragment failed: {response}"

                # ============================================================
                # Step 6: Re-render using alias (Version 3)
                # ============================================================
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": test_alias, "format": "html"},
                )
                response = _parse_response(result)
                assert response.get("status") == "success"
                html_v3 = response.get("data", {}).get("content", "")
                assert "VERSION_ONE" not in html_v3, "Version 1 content should be removed"
                assert "VERSION_TWO" in html_v3, "Version 2 content should remain"

                # ============================================================
                # Step 7: Verify fragment count
                # ============================================================
                result = await session.call_tool(
                    "list_session_fragments",
                    arguments={"session_id": test_alias},
                )
                response = _parse_response(result)
                assert response.get("status") == "success"
                fragments = response.get("data", {}).get("fragments", [])
                assert (
                    len(fragments) == 1
                ), f"Expected 1 fragment after removal, got {len(fragments)}"

                # Clean up
                result = await session.call_tool(
                    "abort_document_session",
                    arguments={"session_id": test_alias},
                )
                response = _parse_response(result)
                assert response.get("status") == "success"

    @pytest.mark.asyncio
    async def test_multi_format_workflow_with_alias(self, mcp_headers):
        """Task 10.4: Render same session to HTML, PDF, and Markdown using alias.

        This test demonstrates multi-format rendering:
        1. Create session with alias
        2. Add content using alias
        3. Render to HTML using alias
        4. Render to PDF using alias
        5. Render to Markdown using alias
        6. Verify all formats contain expected content

        Key assertion: Alias works for all output formats!
        """

        test_alias = "multi-format-report"

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # ============================================================
                # Step 1: Create session with alias
                # ============================================================
                result = await session.call_tool(
                    "create_document_session",
                    arguments={
                        "template_id": "basic_report",
                        "alias": test_alias,
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"Create failed: {response}"

                # Set global parameters
                result = await session.call_tool(
                    "set_global_parameters",
                    arguments={
                        "session_id": test_alias,
                        "parameters": {"title": "Multi-Format Test Document"},
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success"

                # ============================================================
                # Step 2: Add content using alias
                # ============================================================
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": test_alias,
                        "fragment_id": "paragraph",
                        "parameters": {
                            "text": "UNIQUE_CONTENT_MARKER: This text should appear in all formats."
                        },
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success"

                # ============================================================
                # Step 3: Render to HTML using alias
                # ============================================================
                result = await session.call_tool(
                    "get_document",
                    arguments={
                        "session_id": test_alias,
                        "format": "html",
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"HTML render failed: {response}"

                html_content = response.get("data", {}).get("content", "")
                html_format = response.get("data", {}).get("format", "")

                assert html_format == "html", f"Expected format 'html', got '{html_format}'"
                assert "UNIQUE_CONTENT_MARKER" in html_content, "Content missing from HTML"
                assert (
                    "<html" in html_content.lower() or "<!doctype" in html_content.lower()
                ), "Not valid HTML"

                # ============================================================
                # Step 4: Render to PDF using alias
                # ============================================================
                result = await session.call_tool(
                    "get_document",
                    arguments={
                        "session_id": test_alias,
                        "format": "pdf",
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"PDF render failed: {response}"

                pdf_content = response.get("data", {}).get("content", "")
                pdf_format = response.get("data", {}).get("format", "")

                assert pdf_format == "pdf", f"Expected format 'pdf', got '{pdf_format}'"
                assert len(pdf_content) > 100, "PDF content too short (should be base64)"
                # PDF is base64 encoded, so we can't check for text directly
                # But we verify it's a non-trivial size (real PDF)

                # ============================================================
                # Step 5: Render to Markdown using alias
                # ============================================================
                result = await session.call_tool(
                    "get_document",
                    arguments={
                        "session_id": test_alias,
                        "format": "md",
                    },
                )
                response = _parse_response(result)
                assert response.get("status") == "success", f"Markdown render failed: {response}"

                md_content = response.get("data", {}).get("content", "")
                md_format = response.get("data", {}).get("format", "")

                assert md_format == "markdown", f"Expected format 'markdown', got '{md_format}'"
                assert "UNIQUE_CONTENT_MARKER" in md_content, "Content missing from Markdown"

                # ============================================================
                # Step 6: Verify all formats worked with the same alias
                # ============================================================
                # All 3 formats rendered successfully using the alias
                # HTML and Markdown contain the marker text
                # PDF is base64 encoded but has substantial content

                # Clean up
                result = await session.call_tool(
                    "abort_document_session",
                    arguments={"session_id": test_alias},
                )
                response = _parse_response(result)
                assert response.get("status") == "success"

    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_alias(self, mcp_headers):
        """Task 10.5: Verify helpful error handling for non-existent aliases.

        This test demonstrates proper error handling:
        1. Try operations with non-existent alias
        2. Verify SESSION_NOT_FOUND errors are returned
        3. Verify error messages are helpful
        4. Verify recovery suggestions are provided

        Key assertion: Invalid aliases produce helpful, actionable errors!
        """

        # Use an alias that definitely doesn't exist
        fake_alias = "this-session-does-not-exist"

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # ============================================================
                # Test 1: set_global_parameters with non-existent alias
                # ============================================================
                result = await session.call_tool(
                    "set_global_parameters",
                    arguments={
                        "session_id": fake_alias,
                        "parameters": {"title": "Should Fail"},
                    },
                )
                response = _parse_response(result)

                assert response.get("status") == "error", "Should fail with non-existent alias"
                assert (
                    response.get("error_code") == "SESSION_NOT_FOUND"
                ), f"Expected SESSION_NOT_FOUND, got: {response.get('error_code')}"
                assert (
                    "not found" in response.get("message", "").lower()
                ), "Error message should mention 'not found'"

                # ============================================================
                # Test 2: add_fragment with non-existent alias
                # ============================================================
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": fake_alias,
                        "fragment_id": "paragraph",
                        "parameters": {"text": "Should Fail"},
                    },
                )
                response = _parse_response(result)

                assert response.get("status") == "error", "Should fail with non-existent alias"
                assert response.get("error_code") == "SESSION_NOT_FOUND"

                # ============================================================
                # Test 3: get_document with non-existent alias
                # ============================================================
                result = await session.call_tool(
                    "get_document",
                    arguments={
                        "session_id": fake_alias,
                        "format": "html",
                    },
                )
                response = _parse_response(result)

                assert response.get("status") == "error", "Should fail with non-existent alias"
                assert response.get("error_code") == "SESSION_NOT_FOUND"

                # ============================================================
                # Test 4: get_session_status with non-existent alias
                # ============================================================
                result = await session.call_tool(
                    "get_session_status",
                    arguments={"session_id": fake_alias},
                )
                response = _parse_response(result)

                assert response.get("status") == "error", "Should fail with non-existent alias"
                assert response.get("error_code") == "SESSION_NOT_FOUND"

                # ============================================================
                # Test 5: list_session_fragments with non-existent alias
                # ============================================================
                result = await session.call_tool(
                    "list_session_fragments",
                    arguments={"session_id": fake_alias},
                )
                response = _parse_response(result)

                assert response.get("status") == "error", "Should fail with non-existent alias"
                assert response.get("error_code") == "SESSION_NOT_FOUND"

                # ============================================================
                # Test 6: abort_document_session with non-existent alias
                # ============================================================
                result = await session.call_tool(
                    "abort_document_session",
                    arguments={"session_id": fake_alias},
                )
                response = _parse_response(result)

                assert response.get("status") == "error", "Should fail with non-existent alias"
                assert response.get("error_code") == "SESSION_NOT_FOUND"

                # ============================================================
                # Test 7: Verify recovery suggestion is provided
                # ============================================================
                # The error response should suggest using list_active_sessions
                recovery = response.get("recovery_strategy", "")
                # Recovery strategy should mention discovering sessions
                assert len(recovery) > 0, "Should provide recovery strategy"


if __name__ == "__main__":
    """Allow running as standalone script for manual testing."""
    pytest.main([__file__, "-v", "-s"])
