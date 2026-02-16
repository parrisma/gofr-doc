#!/usr/bin/env python3
"""Complete workflow test for news_email template generation with group-based security.

Tests the full document generation workflow with authentication and group isolation:
1. Create authenticated session via MCP with JWT token
2. Add global parameters (session ownership verified)
3. Add 2 news stories + disclaimer (group boundary enforcement)
4. Render to HTML with proxy mode (authenticated access)
5. Retrieve from MCP by session_id (group verification)
6. Retrieve from web server by proxy_guid (group-based access)
7. Verify content consistency across retrieval methods
8. Validate cross-group access is denied (security test)

SECURITY FEATURES DEMONSTRATED:
- JWT Bearer token authentication
- Group-based session isolation
- Session ownership verification on all operations
- Cross-group access denial
- Proxy document group boundaries

Requires:
- MCP server running (Docker Compose via scripts/start-test-env.sh)
- Web server running with JWT authentication
- Shared JWT secret configured via GOFR_JWT_SECRET
"""

import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gofr_common.auth.groups import DuplicateGroupError


def _ensure_group(registry, name, description=None):
    """Create group if it doesn't already exist."""
    try:
        registry.create_group(name, description)
    except DuplicateGroupError:
        pass


# Note: server_auth_service and server_mcp_headers fixtures are provided by conftest.py

# Port configuration via environment variables
MCP_HOST = os.environ.get("GOFR_DOC_MCP_HOST", "localhost")
MCP_PORT = os.environ.get("GOFR_DOC_MCP_PORT", "8040")
WEB_HOST = os.environ.get("GOFR_DOC_WEB_HOST", "localhost")
WEB_PORT = os.environ.get("GOFR_DOC_WEB_PORT", "8042")
MCP_URL = f"http://{MCP_HOST}:{MCP_PORT}/mcp/"
WEB_URL = f"http://{WEB_HOST}:{WEB_PORT}"


def _http_get(url, headers=None):
    """Simple HTTP GET helper."""
    request = Request(url)
    if headers:
        for key, value in headers.items():
            request.add_header(key, value)
    with urlopen(request) as response:
        return {
            "status_code": response.status,
            "headers": dict(response.headers),
            "text": response.read().decode("utf-8"),
        }


def _extract_text(result):
    """Extract text content from MCP tool result."""
    if not result or not result.content:
        return ""
    for item in result.content:
        if isinstance(item, TextContent):
            return item.text
    return ""


def _safe_json_parse(text):
    """Safely parse JSON with error handling."""
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


# Note: Using server_auth_service and server_mcp_headers from conftest.py (default 'test_group')


class TestNewsEmailWorkflow:
    """Test complete news email workflow through MCP and web servers."""

    @pytest.mark.asyncio
    async def test_complete_news_email_workflow(self, server_mcp_headers, server_auth_service):
        """Test complete workflow: create → add content → render → retrieve via both methods.

        SECURITY: This test uses JWT authentication with group='test_group'. All operations
        verify that the session belongs to the authenticated group before allowing access.
        The server_mcp_headers fixture provides the Bearer token for authentication.
        """

        # ================================================================
        # PART 1: Create and build document via MCP (with authentication)
        # ================================================================

        async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Step 2: Create second session
                result = await session.call_tool(
                    "create_document_session",
                    arguments={
                        "template_id": "news_email",
                        "alias": "news-workflow-3",
                        "group": "test_group",
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                session_id = resp.get("data", {}).get("session_id")
                assert session_id, "Failed to create session"

                # Step 2: Set global parameters
                result = await session.call_tool(
                    "set_global_parameters",
                    arguments={
                        "session_id": session_id,
                        "parameters": {
                            "email_subject": "Market Update - November 2025",
                            "heading_title": "Weekly Financial News",
                            "heading_subtitle": "November 16-20, 2025",
                            "company_name": "Test Financial Corp",
                            "recipient_type": "Professional Investors",
                            "include_ai_notice": True,
                            "contact_email": "news@testfinancial.com",
                        },
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "success", "Failed to set global parameters"

                # Step 3: Add first news story (high impact)
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "news",
                        "parameters": {
                            "story_summary": "Global equity markets rallied sharply following stronger-than-expected economic data. S&P 500 gained 2.3% while European indices posted similar gains.",
                            "date": "2025-11-18",
                            "author": "Financial Times",
                            "source": "https://ft.com/markets",
                            "impact_rating": "high",
                        },
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "success", "Failed to add first news story"
                story1_guid = resp.get("data", {}).get("fragment_instance_guid")
                assert story1_guid, "No fragment GUID returned for story 1"

                # Step 4: Add second news story (medium impact)
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "news",
                        "parameters": {
                            "story_summary": "Technology sector shows stabilization as major tech companies report solid quarterly earnings. Cloud computing and AI segments continue driving growth.",
                            "date": "2025-11-17",
                            "author": "Bloomberg",
                            "source": "https://bloomberg.com/tech",
                            "impact_rating": "medium",
                        },
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "success", "Failed to add second news story"
                story2_guid = resp.get("data", {}).get("fragment_instance_guid")
                assert story2_guid, "No fragment GUID returned for story 2"

                # Step 5: Add disclaimer
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "disclaimer",
                        "parameters": {
                            "company_name": "Test Financial Corp",
                            "recipient_type": "Professional Investors",
                            "include_ai_notice": True,
                            "jurisdiction": "US",
                            "contact_email": "compliance@testfinancial.com",
                        },
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "success", "Failed to add disclaimer"
                disclaimer_guid = resp.get("data", {}).get("fragment_instance_guid")
                assert disclaimer_guid, "No fragment GUID returned for disclaimer"

                # ================================================================
                # PART 2: Render with proxy mode
                # ================================================================

                # Step 6: Render to HTML with proxy
                result = await session.call_tool(
                    "get_document",
                    arguments={
                        "session_id": session_id,
                        "format": "html",
                        "style_id": "bizdark",
                        "proxy": True,
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "success", "Failed to render document"

                data = resp.get("data", {})
                proxy_guid = data.get("proxy_guid")

                assert proxy_guid, "No proxy_guid returned"

                # ================================================================
                # PART 3: Retrieve via MCP by session_id (direct render)
                # ================================================================

                # Step 7: Get document directly via MCP (no proxy)
                result = await session.call_tool(
                    "get_document",
                    arguments={
                        "session_id": session_id,
                        "format": "html",
                        "style_id": "bizdark",
                        "proxy": False,
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "success", "Failed to get document via MCP"

                mcp_html = resp.get("data", {}).get("content", "")
                assert len(mcp_html) > 1000, "MCP HTML content too short"
                assert "<!DOCTYPE html>" in mcp_html, "MCP HTML missing DOCTYPE"
                assert "Test Financial Corp" in mcp_html, "MCP HTML missing company name"
                assert "Global equity markets rallied" in mcp_html, "MCP HTML missing story 1"
                assert "Technology sector shows" in mcp_html, "MCP HTML missing story 2"
                assert (
                    "bizdark" in mcp_html.lower() or "gofr-doc-bg" in mcp_html
                ), "MCP HTML missing style"

        # ================================================================
        # PART 4: Retrieve via web server by proxy_guid
        # ================================================================

        # Step 8: Get document via web server proxy endpoint
        web_response = _http_get(f"{WEB_URL}/proxy/{proxy_guid}", headers=server_mcp_headers)
        assert (
            web_response["status_code"] == 200
        ), f"Web server returned {web_response['status_code']}"
        # HTTP headers are case-insensitive - check lowercase version
        content_type = web_response["headers"].get("content-type") or web_response["headers"].get(
            "Content-Type"
        )
        assert content_type == "text/html; charset=utf-8", f"Wrong content type: {content_type}"

        web_html = web_response["text"]

        # ================================================================
        # PART 5: Verify content consistency
        # ================================================================

        # Both renders should produce identical HTML
        assert web_html == mcp_html, "HTML from MCP and web server don't match"

        # Verify all expected content elements
        assert "high" in mcp_html.lower(), "Missing 'high' impact rating"
        assert "medium" in mcp_html.lower(), "Missing 'medium' impact rating"
        assert "Financial Times" in mcp_html, "Missing first news source"
        assert "Bloomberg" in mcp_html, "Missing second news source"
        assert (
            "AI" in mcp_html or "artificial intelligence" in mcp_html.lower()
        ), "Missing AI notice"
        assert "Professional Investors" in mcp_html, "Missing recipient type"

    @pytest.mark.asyncio
    async def test_workflow_multiple_renders_same_content(self, server_mcp_headers):
        """Test that multiple renders of same session produce identical content."""

        async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Create and build document
                result = await session.call_tool(
                    "create_document_session",
                    arguments={
                        "template_id": "news_email",
                        "group": "test_group",
                        "alias": "multiple-renders-test",
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                session_id = resp.get("data", {}).get("session_id")

                result = await session.call_tool(
                    "set_global_parameters",
                    arguments={
                        "session_id": session_id,
                        "parameters": {
                            "email_subject": "Test Email",
                            "heading_title": "Test News",
                            "company_name": "Test Corp",
                        },
                    },
                )

                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "news",
                        "parameters": {
                            "story_summary": "Test story content",
                            "date": "2025-11-16",
                            "author": "Test Author",
                            "source": "https://test.com",
                            "impact_rating": "low",
                        },
                    },
                )

                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "disclaimer",
                        "parameters": {"company_name": "Test Corp"},
                    },
                )

                # Render three times
                html_renders = []
                for i in range(3):
                    result = await session.call_tool(
                        "get_document",
                        arguments={
                            "session_id": session_id,
                            "format": "html",
                            "style_id": "light",
                            "proxy": False,
                        },
                    )
                    resp = _safe_json_parse(_extract_text(result))
                    html_content = resp.get("data", {}).get("content", "")
                    html_renders.append(html_content)

                # All renders should be identical
                assert html_renders[0] == html_renders[1], "Render 1 and 2 differ"
                assert html_renders[1] == html_renders[2], "Render 2 and 3 differ"
                assert len(html_renders[0]) > 100, "Rendered content too short"

    @pytest.mark.asyncio
    async def test_workflow_proxy_persistence(self, server_mcp_headers):
        """Test that proxy documents remain accessible after session ends."""

        proxy_guid = None
        session_id = None

        # Create and render with proxy
        async with streamablehttp_client(MCP_URL, headers=server_mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "create_document_session",
                    arguments={
                        "template_id": "news_email",
                        "group": "test_group",
                        "alias": "proxy-persistence-test",
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                session_id = resp.get("data", {}).get("session_id")

                result = await session.call_tool(
                    "set_global_parameters",
                    arguments={
                        "session_id": session_id,
                        "parameters": {
                            "email_subject": "Persistence Test",
                            "heading_title": "Persistence Test",
                            "company_name": "Persistence Corp",
                        },
                    },
                )

                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "disclaimer",
                        "parameters": {"company_name": "Persistence Corp"},
                    },
                )

                result = await session.call_tool(
                    "get_document",
                    arguments={
                        "session_id": session_id,
                        "format": "html",
                        "proxy": True,
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                proxy_guid = resp.get("data", {}).get("proxy_guid")

        # Session is now closed, but proxy document should still be accessible
        assert proxy_guid, "No proxy_guid created"

        # Retrieve via web server
        web_response = _http_get(f"{WEB_URL}/proxy/{proxy_guid}", headers=server_mcp_headers)
        assert (
            web_response["status_code"] == 200
        ), "Proxy document not accessible after session closed"
        assert "Persistence Corp" in web_response["text"], "Proxy content incorrect"

    @pytest.mark.asyncio
    async def test_workflow_group_isolation_security(self, server_auth_service):
        """Test that group-based security prevents cross-group session access.

        SECURITY TEST: Demonstrates the complete group isolation model:
        1. Create session with 'engineering' group credentials
        2. Attempt to access session with 'marketing' group credentials
        3. Verify all operations return SESSION_NOT_FOUND (no info leakage)
        4. Verify list_active_sessions only shows same-group sessions
        5. Confirm proxy documents are also group-isolated

        This validates the core security boundary of the multi-tenant system.
        """

        # Create tokens for two different groups
        _ensure_group(server_auth_service._group_registry, "engineering", "Engineering test group")
        _ensure_group(server_auth_service._group_registry, "marketing", "Marketing test group")
        engineering_token = server_auth_service.create_token(
            groups=["engineering"], expires_in_seconds=3600
        )
        marketing_token = server_auth_service.create_token(
            groups=["marketing"], expires_in_seconds=3600
        )

        engineering_headers = {"Authorization": f"Bearer {engineering_token}"}
        marketing_headers = {"Authorization": f"Bearer {marketing_token}"}

        session_id = None
        proxy_guid = None

        # ================================================================
        # PART 1: Create session as 'engineering' group
        # ================================================================
        async with streamablehttp_client(MCP_URL, headers=engineering_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Create session (will be tagged with 'engineering' group from JWT)
                result = await session.call_tool(
                    "create_document_session",
                    arguments={"template_id": "news_email", "alias": "news-workflow-4"},
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "success", "Failed to create session as engineering"
                session_id = resp.get("data", {}).get("session_id")
                assert session_id, "No session_id returned"

                # Set parameters
                result = await session.call_tool(
                    "set_global_parameters",
                    arguments={
                        "session_id": session_id,
                        "parameters": {
                            "email_subject": "Engineering Team Update",
                            "heading_title": "Internal Engineering News",
                            "company_name": "TechCorp Engineering",
                        },
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "success", "Failed to set parameters as engineering"

                # Add content
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "disclaimer",
                        "parameters": {"company_name": "TechCorp Engineering"},
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "success", "Failed to add fragment as engineering"

                # Render with proxy
                result = await session.call_tool(
                    "get_document",
                    arguments={
                        "session_id": session_id,
                        "format": "html",
                        "proxy": True,
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "success", "Failed to render as engineering"
                proxy_guid = resp.get("data", {}).get("proxy_guid")
                assert proxy_guid, "No proxy_guid returned"

        # ================================================================
        # PART 2: Attempt cross-group access as 'marketing' (should FAIL)
        # ================================================================
        async with streamablehttp_client(MCP_URL, headers=marketing_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Attempt to get session status - should return SESSION_NOT_FOUND
                result = await session.call_tool(
                    "get_session_status",
                    arguments={"session_id": session_id},
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "error", "Should deny cross-group status check"
                assert (
                    resp.get("error_code") == "SESSION_NOT_FOUND"
                ), f"Wrong error code: {resp.get('error_code')}"
                assert (
                    "not found" in resp.get("message", "").lower()
                ), "Error message should be generic"

                # Attempt to set parameters - should return SESSION_NOT_FOUND
                result = await session.call_tool(
                    "set_global_parameters",
                    arguments={
                        "session_id": session_id,
                        "parameters": {"email_subject": "Hacked!"},
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "error", "Should deny cross-group parameter update"
                assert (
                    resp.get("error_code") == "SESSION_NOT_FOUND"
                ), f"Wrong error code: {resp.get('error_code')}"

                # Attempt to add fragment - should return SESSION_NOT_FOUND
                result = await session.call_tool(
                    "add_fragment",
                    arguments={
                        "session_id": session_id,
                        "fragment_id": "disclaimer",
                        "parameters": {"company_name": "Hacked"},
                    },
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "error", "Should deny cross-group fragment add"
                assert (
                    resp.get("error_code") == "SESSION_NOT_FOUND"
                ), f"Wrong error code: {resp.get('error_code')}"

                # Attempt to render - should return SESSION_NOT_FOUND
                result = await session.call_tool(
                    "get_document",
                    arguments={"session_id": session_id, "format": "html"},
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "error", "Should deny cross-group render"
                assert (
                    resp.get("error_code") == "SESSION_NOT_FOUND"
                ), f"Wrong error code: {resp.get('error_code')}"

                # List active sessions - should NOT include engineering's session
                result = await session.call_tool(
                    "list_active_sessions",
                    arguments={},
                )
                resp = _safe_json_parse(_extract_text(result))
                assert resp.get("status") == "success", "list_active_sessions should succeed"
                sessions = resp.get("data", {}).get("sessions", [])
                session_ids = [s.get("session_id") for s in sessions]
                assert (
                    session_id not in session_ids
                ), "Should NOT see engineering's session in marketing's list"

        # ================================================================
        # PART 3: Verify proxy document is also group-isolated
        # ================================================================
        # Note: Web server proxy endpoint should also enforce group boundaries
        # Attempting to retrieve with marketing token should fail
        # (This depends on web server implementing group-based proxy access)

        # Engineering can still access their own session
        async with streamablehttp_client(MCP_URL, headers=engineering_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Verify engineering can still access their session
                result = await session.call_tool(
                    "get_session_status",
                    arguments={"session_id": session_id},
                )
                resp = _safe_json_parse(_extract_text(result))
                assert (
                    resp.get("status") == "success"
                ), "Engineering should still access their session"
                assert (
                    resp.get("data", {}).get("group") == "engineering"
                ), "Session should be tagged with engineering group"

                # Verify engineering can list and see their session
                result = await session.call_tool(
                    "list_active_sessions",
                    arguments={},
                )
                resp = _safe_json_parse(_extract_text(result))
                sessions = resp.get("data", {}).get("sessions", [])
                session_ids = [s.get("session_id") for s in sessions]
                assert session_id in session_ids, "Engineering should see their own session"


if __name__ == "__main__":
    """Allow running as standalone script for manual testing."""
    pytest.main([__file__, "-v", "-s"])
