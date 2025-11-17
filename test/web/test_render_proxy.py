#!/usr/bin/env python3
"""Test proxy-based rendering and retrieval for web server.

Tests the proxy rendering workflow:
1. Create and finalize a session via MCP
2. Render with proxy=true to get proxy_guid
3. Retrieve document using GET /proxy/{proxy_guid}

Requires MCP server running on port 8011 for test setup.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from fastapi.testclient import TestClient
from app.web_server import DocoWebServer
from app.sessions import SessionManager, SessionStore
from app.templates.registry import TemplateRegistry
from app.logger import session_logger
from app.config import get_default_sessions_dir
import uuid


@pytest.fixture
def client():
    """Create a test client for the web server"""
    test_data_dir = Path(__file__).parent.parent / "render" / "data" / "docs"
    from app.auth import AuthService

    auth_service = AuthService(
        secret_key="test-secret-key-for-secure-testing-do-not-use-in-production",
        token_store_path="/tmp/doco_test_tokens.json",
    )
    server = DocoWebServer(
        auth_service=auth_service,
        templates_dir=str(test_data_dir / "templates"),
        fragments_dir=str(test_data_dir / "fragments"),
        styles_dir=str(test_data_dir / "styles"),
        require_auth=False,
    )
    return TestClient(server.app)


@pytest.fixture
def session_manager():
    """Create a session manager for test setup"""
    test_data_dir = Path(__file__).parent.parent / "render" / "data" / "docs"
    session_store = SessionStore(base_dir=get_default_sessions_dir(), logger=session_logger)
    template_registry = TemplateRegistry(str(test_data_dir / "templates"), session_logger)
    return SessionManager(
        session_store=session_store, template_registry=template_registry, logger=session_logger
    )


class TestProxyRenderEndpoint:
    """Test POST /render/{session_id} with proxy mode"""

    @pytest.mark.asyncio
    async def test_render_with_proxy_returns_guid(self, client, session_manager):
        """Test that proxy render returns proxy_guid instead of content"""
        # Create a test session
        result = await session_manager.create_session(template_id="news_email", group="public")
        session_id = result.session_id

        # Set global parameters
        await session_manager.set_global_parameters(
            session_id=session_id,
            parameters={
                "company_name": "Test Corp",
                "email_subject": "Test Email",
                "heading_title": "Market Update",
            },
        )

        # Add fragments
        await session_manager.add_fragment(
            session_id=session_id,
            fragment_id="news",
            parameters={
                "story_summary": "Test Story 1",
                "date": "2025-01-01",
                "source": "Test Source",
                "author": "Test Author",
                "impact_rating": "high",
            },
        )

        await session_manager.add_fragment(
            session_id=session_id,
            fragment_id="disclaimer",
            parameters={
                "company_name": "Test Corp",
                "include_ai_notice": True,
            },
        )

        # Finalize session

        # Render with proxy=true
        response = client.post(
            f"/render/{session_id}",
            json={"format": "html", "style_id": "bizdark", "proxy": True},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "proxy_guid" in data["data"]
        assert "format" in data["data"]
        assert data["data"]["format"] == "html"

        # Verify proxy_guid is a valid UUID
        proxy_guid = data["data"]["proxy_guid"]
        try:
            uuid.UUID(proxy_guid)
        except ValueError:
            pytest.fail(f"proxy_guid '{proxy_guid}' is not a valid UUID")

    @pytest.mark.asyncio
    async def test_render_without_proxy_returns_content(self, client, session_manager):
        """Test that non-proxy render returns HTML content directly"""
        # Create a minimal session
        result = await session_manager.create_session(template_id="news_email", group="public")
        session_id = result.session_id

        await session_manager.set_global_parameters(
            session_id=session_id,
            parameters={
                "company_name": "Test Corp",
                "heading_title": "Market Update",
                "email_subject": "Test Email",
            },
        )

        await session_manager.add_fragment(
            session_id=session_id,
            fragment_id="disclaimer",
            parameters={"company_name": "Test Corp"},
        )

        # Render without proxy (default is proxy=false)
        response = client.post(
            f"/render/{session_id}", json={"format": "html", "style_id": "bizdark"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"

        # Should return HTML content
        html_content = response.text
        assert "<!DOCTYPE html>" in html_content
        assert "<html" in html_content
        assert "Test Corp" in html_content

    @pytest.mark.asyncio
    async def test_render_invalid_session_returns_404(self, client):
        """Test that rendering non-existent session returns 404"""
        fake_session_id = str(uuid.uuid4())

        response = client.post(f"/render/{fake_session_id}", json={"format": "html"})

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "error" in data["detail"]
        assert data["detail"]["error"] == "SESSION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_render_with_invalid_format_returns_400(self, client, session_manager):
        """Test that invalid output format returns 400"""
        # Create a minimal session
        result = await session_manager.create_session(template_id="news_email", group="public")
        session_id = result.session_id

        await session_manager.set_global_parameters(
            session_id=session_id,
            parameters={
                "company_name": "Test Corp",
                "heading_title": "Market Update",
                "email_subject": "Test Email",
            },
        )

        # Try to render with invalid format
        response = client.post(f"/render/{session_id}", json={"format": "invalid_format_xyz"})

        assert response.status_code == 400


class TestProxyRetrievalEndpoint:
    """Test GET /proxy/{proxy_guid} endpoint"""

    @pytest.mark.asyncio
    async def test_get_proxy_document_returns_html(self, client, session_manager):
        """Test retrieving a stored proxy document returns HTML content"""
        # Setup: Create and render with proxy
        result = await session_manager.create_session(template_id="news_email", group="public")
        session_id = result.session_id

        await session_manager.set_global_parameters(
            session_id=session_id,
            parameters={
                "company_name": "Proxy Test Corp",
                "heading_title": "Market Update",
                "email_subject": "Proxy Test",
            },
        )

        await session_manager.add_fragment(
            session_id=session_id,
            fragment_id="disclaimer",
            parameters={"company_name": "Proxy Test Corp", "include_ai_notice": True},
        )

        # Render with proxy to get GUID
        render_response = client.post(
            f"/render/{session_id}",
            json={"format": "html", "style_id": "dark", "proxy": True},
        )

        assert render_response.status_code == 200
        proxy_guid = render_response.json()["data"]["proxy_guid"]

        # Now retrieve the document via proxy
        proxy_response = client.get(f"/proxy/{proxy_guid}")

        assert proxy_response.status_code == 200
        assert proxy_response.headers["content-type"] == "text/html; charset=utf-8"

        # Verify content
        html_content = proxy_response.text
        assert "<!DOCTYPE html>" in html_content
        assert "Proxy Test Corp" in html_content

    @pytest.mark.asyncio
    async def test_get_proxy_document_with_group_parameter(self, client, session_manager):
        """Test retrieving proxy document with explicit group parameter"""
        # Setup session
        result = await session_manager.create_session(template_id="news_email", group="public")
        session_id = result.session_id

        await session_manager.set_global_parameters(
            session_id=session_id,
            parameters={
                "company_name": "Group Test Corp",
                "heading_title": "Market Update",
                "email_subject": "Group Test",
            },
        )

        await session_manager.add_fragment(
            session_id=session_id,
            fragment_id="disclaimer",
            parameters={"company_name": "Group Test Corp"},
        )

        # Render with proxy
        render_response = client.post(
            f"/render/{session_id}",
            json={"format": "html", "style_id": "light", "proxy": True},
        )

        proxy_guid = render_response.json()["data"]["proxy_guid"]

        # Retrieve proxy document (group verified from stored metadata)
        proxy_response = client.get(f"/proxy/{proxy_guid}")

        assert proxy_response.status_code == 200
        assert "Group Test Corp" in proxy_response.text

    def test_get_proxy_document_invalid_guid_returns_404(self, client):
        """Test that invalid proxy GUID returns 404"""
        fake_guid = str(uuid.uuid4())

        response = client.get(f"/proxy/{fake_guid}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_get_proxy_document_invalid_group_returns_404(self, client, session_manager):
        """Test retrieving non-existent proxy document returns 404."""
        fake_guid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/proxy/{fake_guid}")

    @pytest.mark.asyncio
    async def test_get_proxy_document_different_formats(self, client, session_manager):
        """Test retrieving proxy documents in different formats"""
        # Create session
        result = await session_manager.create_session(template_id="news_email", group="public")
        session_id = result.session_id

        await session_manager.set_global_parameters(
            session_id=session_id,
            parameters={
                "company_name": "Format Test Corp",
                "heading_title": "Market Update",
                "email_subject": "Format Test",
            },
        )

        await session_manager.add_fragment(
            session_id=session_id,
            fragment_id="disclaimer",
            parameters={"company_name": "Format Test Corp"},
        )

        # Test HTML format
        html_render = client.post(
            f"/render/{session_id}",
            json={"format": "html", "style_id": "dark", "proxy": True},
        )
        html_guid = html_render.json()["data"]["proxy_guid"]
        html_response = client.get(f"/proxy/{html_guid}")
        assert html_response.status_code == 200
        assert html_response.headers["content-type"] == "text/html; charset=utf-8"

        # Test Markdown format
        md_render = client.post(
            f"/render/{session_id}",
            json={"format": "markdown", "style_id": "dark", "proxy": True},
        )
        md_guid = md_render.json()["data"]["proxy_guid"]
        # Retrieve Markdown
        md_response = client.get(f"/proxy/{md_guid}")
        assert md_response.status_code == 200
        assert md_response.headers["content-type"] == "text/markdown; charset=utf-8"


class TestProxyWorkflow:
    """Test complete proxy workflow: render → store → retrieve"""

    @pytest.mark.asyncio
    async def test_complete_proxy_workflow(self, client, session_manager):
        """Test full workflow from session creation to proxy retrieval"""
        # Step 1: Create session with news stories
        result = await session_manager.create_session(template_id="news_email", group="public")
        session_id = result.session_id

        # Step 2: Set global params
        await session_manager.set_global_parameters(
            session_id=session_id,
            parameters={
                "company_name": "Workflow Test Inc",
                "heading_title": "Market Update",
                "email_subject": "Market Update",
            },
        )

        # Step 3: Add news fragments
        await session_manager.add_fragment(
            session_id=session_id,
            fragment_id="news",
            parameters={
                "story_summary": "Tech stocks rally on positive earnings",
                "date": "2025-11-15",
                "source": "Financial Times",
                "author": "Market Reporter",
                "impact_rating": "high",
            },
        )

        await session_manager.add_fragment(
            session_id=session_id,
            fragment_id="news",
            parameters={
                "story_summary": "Central bank holds rates steady",
                "date": "2025-11-14",
                "source": "Reuters",
                "author": "Economic Analyst",
                "impact_rating": "medium",
            },
        )

        # Step 4: Add disclaimer
        await session_manager.add_fragment(
            session_id=session_id,
            fragment_id="disclaimer",
            parameters={
                "company_name": "Workflow Test Inc",
                "recipient_type": "investor",
                "include_ai_notice": True,
                "jurisdiction": "US",
                "contact_email": "compliance@example.com",
            },
        )

        # Step 5: Finalize

        # Step 6: Render with proxy
        render_response = client.post(
            f"/render/{session_id}",
            json={"format": "html", "style_id": "bizdark", "proxy": True},
        )

        assert render_response.status_code == 200
        proxy_data = render_response.json()["data"]
        assert "proxy_guid" in proxy_data
        proxy_guid = proxy_data["proxy_guid"]

        # Step 7: Retrieve from proxy
        proxy_response = client.get(f"/proxy/{proxy_guid}")

        assert proxy_response.status_code == 200
        html_content = proxy_response.text

        # Step 8: Verify all content is present
        assert "<!DOCTYPE html>" in html_content
        assert "Workflow Test Inc" in html_content
        assert "Tech stocks rally" in html_content
        assert "Central bank holds rates" in html_content
        assert "Financial Times" in html_content
        assert "Reuters" in html_content
        assert "high" in html_content.lower()  # Impact rating
        assert "medium" in html_content.lower()  # Impact rating
        assert "AI" in html_content or "artificial intelligence" in html_content.lower()

    @pytest.mark.asyncio
    async def test_multiple_renders_create_different_guids(self, client, session_manager):
        """Test that rendering same session multiple times creates different proxy GUIDs"""
        # Create session
        result = await session_manager.create_session(template_id="news_email", group="public")
        session_id = result.session_id

        await session_manager.set_global_parameters(
            session_id=session_id,
            parameters={
                "company_name": "Multi Render Corp",
                "heading_title": "Market Update",
                "email_subject": "Test",
            },
        )

        await session_manager.add_fragment(
            session_id=session_id,
            fragment_id="disclaimer",
            parameters={"company_name": "Multi Render Corp"},
        )

        # Render twice
        response1 = client.post(
            f"/render/{session_id}",
            json={"format": "html", "style_id": "dark", "proxy": True},
        )
        guid1 = response1.json()["data"]["proxy_guid"]

        response2 = client.post(
            f"/render/{session_id}",
            json={"format": "html", "style_id": "dark", "proxy": True},
        )
        guid2 = response2.json()["data"]["proxy_guid"]

        # GUIDs should be different
        assert guid1 != guid2

        # Both should be retrievable
        assert client.get(f"/proxy/{guid1}").status_code == 200
        assert client.get(f"/proxy/{guid2}").status_code == 200
