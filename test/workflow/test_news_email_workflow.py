#!/usr/bin/env python3
"""Complete workflow test for news_email template generation.

Tests the full document generation workflow:
1. Create session via MCP
2. Add global parameters
3. Add 2 news stories + disclaimer
4. Render to HTML with proxy mode
5. Retrieve from MCP by session_id
6. Retrieve from web server by proxy_guid
7. Verify content consistency

Requires:
- MCP server running on port 8011
- Web server running on port 8010
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import json
from urllib.request import urlopen, Request
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
from mcp.types import TextContent

# Note: auth_service and mcp_headers fixtures are now provided by conftest.py

# Port configuration via environment variables (defaults to production ports)
MCP_PORT = os.environ.get("DOCO_MCP_PORT", "8011")
WEB_PORT = os.environ.get("DOCO_WEB_PORT", "8010")

MCP_URL = f"http://localhost:{MCP_PORT}/mcp/"
WEB_URL = f"http://localhost:{WEB_PORT}"


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


# Note: Using auth_service and mcp_headers from conftest.py (default 'test_group')


class TestNewsEmailWorkflow:
    """Test complete news email workflow through MCP and web servers."""

    @pytest.mark.asyncio
    async def test_complete_news_email_workflow(self, mcp_headers):
        """Test complete workflow: create → add content → render → retrieve via both methods."""

        # ================================================================
        # PART 1: Create and build document via MCP
        # ================================================================

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Step 1: Create session
                result = await session.call_tool(
                    "create_document_session",
                    arguments={"template_id": "news_email", "group": "test_group"},
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
                    "bizdark" in mcp_html.lower() or "doco-bg" in mcp_html
                ), "MCP HTML missing style"

        # ================================================================
        # PART 4: Retrieve via web server by proxy_guid
        # ================================================================

        # Step 8: Get document via web server proxy endpoint
        web_response = _http_get(f"{WEB_URL}/proxy/{proxy_guid}", headers=mcp_headers)
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
    async def test_workflow_multiple_renders_same_content(self, mcp_headers):
        """Test that multiple renders of same session produce identical content."""

        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Create and build document
                result = await session.call_tool(
                    "create_document_session",
                    arguments={"template_id": "news_email", "group": "test_group"},
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
    async def test_workflow_proxy_persistence(self, mcp_headers):
        """Test that proxy documents remain accessible after session ends."""

        proxy_guid = None
        session_id = None

        # Create and render with proxy
        async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "create_document_session",
                    arguments={"template_id": "news_email", "group": "test_group"},
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
        web_response = _http_get(f"{WEB_URL}/proxy/{proxy_guid}", headers=mcp_headers)
        assert (
            web_response["status_code"] == 200
        ), "Proxy document not accessible after session closed"
        assert "Persistence Corp" in web_response["text"], "Proxy content incorrect"


if __name__ == "__main__":
    """Allow running as standalone script for manual testing."""
    pytest.main([__file__, "-v", "-s"])
