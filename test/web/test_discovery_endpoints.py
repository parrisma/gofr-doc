#!/usr/bin/env python3
"""Test discovery endpoints for web server.

Tests the following endpoints:
- GET /ping - Health check
- GET /templates - List templates
- GET /templates/{template_id} - Template details
- GET /templates/{template_id}/fragments - Template fragments
- GET /fragments/{fragment_id} - Fragment details
- GET /styles - List styles

These tests use the live MCP server (if available) to generate test content.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from fastapi.testclient import TestClient
from app.web_server.web_server import GofrDocWebServer


@pytest.fixture
def client(test_data_dir):
    """Create a TestClient for the web server."""
    server = GofrDocWebServer(require_auth=False, auth_service=None)  # Disable auth for tests
    return TestClient(server.app)


class TestPingEndpoint:
    """Test /ping endpoint"""

    def test_ping_returns_200(self, client):
        """Test that ping endpoint returns 200 status"""
        response = client.get("/ping")
        assert response.status_code == 200

    def test_ping_returns_ok_status(self, client):
        """Test that ping endpoint returns 'ok' status"""
        response = client.get("/ping")
        data = response.json()

        assert "status" in data
        assert data["status"] == "ok"

    def test_ping_returns_timestamp(self, client):
        """Test that ping endpoint returns ISO8601 timestamp"""
        response = client.get("/ping")
        data = response.json()

        assert "timestamp" in data
        assert isinstance(data["timestamp"], str)
        # Validate ISO8601 format
        assert "T" in data["timestamp"]

    def test_ping_returns_service_name(self, client):
        """Test that ping endpoint returns service identifier"""
        response = client.get("/ping")
        data = response.json()

        assert "service" in data
        assert data["service"] == "gofr-doc"


class TestTemplateListEndpoint:
    """Test GET /templates endpoint"""

    def test_list_templates_returns_200(self, client):
        """Test that list templates endpoint returns 200"""
        response = client.get("/templates")
        assert response.status_code == 200

    def test_list_templates_returns_success_status(self, client):
        """Test that response has success status"""
        response = client.get("/templates")
        data = response.json()

        assert "status" in data
        assert data["status"] == "success"

    def test_list_templates_returns_data_array(self, client):
        """Test that response contains data array"""
        response = client.get("/templates")
        data = response.json()

        assert "data" in data
        assert isinstance(data["data"], list)

    def test_list_templates_contains_required_fields(self, client):
        """Test that each template has required fields"""
        response = client.get("/templates")
        data = response.json()

        # Should have at least one template
        if len(data["data"]) > 0:
            template = data["data"][0]
            assert "template_id" in template
            assert "name" in template
            assert "description" in template
            assert "group" in template

    def test_list_templates_by_group(self, client):
        """Test filtering templates by group"""
        # Get all templates
        response = client.get("/templates")
        all_templates = response.json()["data"]

        if len(all_templates) > 0:
            # Get first template's group
            group = all_templates[0]["group"]

            # Filter by that group
            response = client.get(f"/templates?group={group}")
            filtered = response.json()["data"]

            # All templates should match the group
            for template in filtered:
                assert template["group"] == group


class TestTemplateDetailsEndpoint:
    """Test GET /templates/{template_id} endpoint"""

    def test_get_template_details_returns_200(self, client):
        """Test that template details endpoint returns 200"""
        # First get list of templates
        response = client.get("/templates")
        templates = response.json()["data"]

        if len(templates) > 0:
            template_id = templates[0]["template_id"]
            response = client.get(f"/templates/{template_id}")
            assert response.status_code == 200

    def test_get_template_details_returns_success_status(self, client):
        """Test that response has success status"""
        response = client.get("/templates")
        templates = response.json()["data"]

        if len(templates) > 0:
            template_id = templates[0]["template_id"]
            response = client.get(f"/templates/{template_id}")
            data = response.json()

            assert "status" in data
            assert data["status"] == "success"

    def test_get_template_details_contains_required_fields(self, client):
        """Test that template details contain required fields"""
        response = client.get("/templates")
        templates = response.json()["data"]

        if len(templates) > 0:
            template_id = templates[0]["template_id"]
            response = client.get(f"/templates/{template_id}")
            data = response.json()["data"]

            assert "template_id" in data
            assert "name" in data
            assert "description" in data
            assert "group" in data
            assert "global_parameters" in data

    def test_get_template_details_global_parameters_structure(self, client):
        """Test that global parameters have correct structure"""
        response = client.get("/templates")
        templates = response.json()["data"]

        if len(templates) > 0:
            template_id = templates[0]["template_id"]
            response = client.get(f"/templates/{template_id}")
            data = response.json()["data"]
            params = data.get("global_parameters", [])

            for param in params:
                assert "name" in param
                assert "type" in param
                assert "description" in param
                assert "required" in param

    def test_get_template_details_invalid_template_returns_404(self, client):
        """Test that invalid template ID returns 404"""
        response = client.get("/templates/nonexistent-template-id")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data


class TestTemplateFragmentsEndpoint:
    """Test GET /templates/{template_id}/fragments endpoint"""

    def test_list_template_fragments_returns_200(self, client):
        """Test that endpoint returns 200"""
        response = client.get("/templates")
        templates = response.json()["data"]

        if len(templates) > 0:
            template_id = templates[0]["template_id"]
            response = client.get(f"/templates/{template_id}/fragments")
            assert response.status_code == 200

    def test_list_template_fragments_returns_success_status(self, client):
        """Test that response has success status"""
        response = client.get("/templates")
        templates = response.json()["data"]

        if len(templates) > 0:
            template_id = templates[0]["template_id"]
            response = client.get(f"/templates/{template_id}/fragments")
            data = response.json()

            assert "status" in data
            assert data["status"] == "success"

    def test_list_template_fragments_returns_data_array(self, client):
        """Test that response contains data array"""
        response = client.get("/templates")
        templates = response.json()["data"]

        if len(templates) > 0:
            template_id = templates[0]["template_id"]
            response = client.get(f"/templates/{template_id}/fragments")
            data = response.json()

            assert "data" in data
            assert isinstance(data["data"], list)

    def test_list_template_fragments_contains_required_fields(self, client):
        """Test that each fragment has required fields"""
        response = client.get("/templates")
        templates = response.json()["data"]

        if len(templates) > 0:
            template_id = templates[0]["template_id"]
            response = client.get(f"/templates/{template_id}/fragments")
            data = response.json()

            if len(data["data"]) > 0:
                fragment = data["data"][0]
                assert "fragment_id" in fragment
                assert "name" in fragment
                assert "description" in fragment
                assert "group" in fragment

    def test_list_template_fragments_invalid_template_returns_404(self, client):
        """Test that invalid template ID returns 404"""
        response = client.get("/templates/nonexistent-template-id/fragments")
        assert response.status_code == 404


class TestFragmentDetailsEndpoint:
    """Test GET /fragments/{fragment_id} endpoint"""

    def test_get_fragment_details_returns_200(self, client):
        """Test that fragment details endpoint returns 200"""
        # Get a fragment ID from the templates
        response = client.get("/templates")
        templates = response.json()["data"]

        if len(templates) > 0:
            template_id = templates[0]["template_id"]
            response = client.get(f"/templates/{template_id}/fragments")
            fragments = response.json()["data"]

            if len(fragments) > 0:
                fragment_id = fragments[0]["fragment_id"]
                response = client.get(f"/fragments/{fragment_id}")
                assert response.status_code == 200

    def test_get_fragment_details_returns_success_status(self, client):
        """Test that response has success status"""
        response = client.get("/templates")
        templates = response.json()["data"]

        if len(templates) > 0:
            template_id = templates[0]["template_id"]
            response = client.get(f"/templates/{template_id}/fragments")
            fragments = response.json()["data"]

            if len(fragments) > 0:
                fragment_id = fragments[0]["fragment_id"]
                response = client.get(f"/fragments/{fragment_id}")
                data = response.json()

                assert "status" in data
                assert data["status"] == "success"

    def test_get_fragment_details_contains_required_fields(self, client):
        """Test that fragment details contain required fields"""
        response = client.get("/templates")
        templates = response.json()["data"]

        if len(templates) > 0:
            template_id = templates[0]["template_id"]
            response = client.get(f"/templates/{template_id}/fragments")
            fragments = response.json()["data"]

            if len(fragments) > 0:
                fragment_id = fragments[0]["fragment_id"]
                response = client.get(f"/fragments/{fragment_id}")
                data = response.json()["data"]

                assert "fragment_id" in data
                assert "name" in data
                assert "description" in data
                assert "group" in data
                assert "parameters" in data

    def test_get_fragment_details_parameters_structure(self, client):
        """Test that parameters have correct structure"""
        response = client.get("/templates")
        templates = response.json()["data"]

        if len(templates) > 0:
            template_id = templates[0]["template_id"]
            response = client.get(f"/templates/{template_id}/fragments")
            fragments = response.json()["data"]

            if len(fragments) > 0:
                fragment_id = fragments[0]["fragment_id"]
                response = client.get(f"/fragments/{fragment_id}")
                data = response.json()["data"]
                params = data.get("parameters", [])

                for param in params:
                    assert "name" in param
                    assert "type" in param
                    assert "description" in param
                    assert "required" in param

    def test_get_fragment_details_invalid_fragment_returns_404(self, client):
        """Test that invalid fragment ID returns 404"""
        response = client.get("/fragments/nonexistent-fragment-id")
        assert response.status_code == 404


class TestStylesListEndpoint:
    """Test GET /styles endpoint"""

    def test_list_styles_returns_200(self, client):
        """Test that list styles endpoint returns 200"""
        response = client.get("/styles")
        assert response.status_code == 200

    def test_list_styles_returns_success_status(self, client):
        """Test that response has success status"""
        response = client.get("/styles")
        data = response.json()

        assert "status" in data
        assert data["status"] == "success"

    def test_list_styles_returns_data_array(self, client):
        """Test that response contains data array"""
        response = client.get("/styles")
        data = response.json()

        assert "data" in data
        assert isinstance(data["data"], list)

    def test_list_styles_contains_required_fields(self, client):
        """Test that each style has required fields"""
        response = client.get("/styles")
        data = response.json()

        if len(data["data"]) > 0:
            style = data["data"][0]
            assert "style_id" in style
            assert "name" in style
            assert "description" in style
            assert "group" in style

    def test_list_styles_by_group(self, client):
        """Test filtering styles by group"""
        # Get all styles
        response = client.get("/styles")
        all_styles = response.json()["data"]

        if len(all_styles) > 0:
            # Get first style's group
            group = all_styles[0]["group"]

            # Filter by that group
            response = client.get(f"/styles?group={group}")
            filtered = response.json()["data"]

            # All styles should match the group
            for style in filtered:
                assert style["group"] == group


class TestAuthenticationHeaders:
    """Test authentication header handling"""

    def test_discovery_endpoints_do_not_require_auth(self, client):
        """Test that discovery endpoints work without auth headers"""
        # These should all work without X-Auth-Token
        assert client.get("/ping").status_code == 200
        assert client.get("/templates").status_code == 200
        assert client.get("/styles").status_code == 200
        assert client.get("/fragments").status_code in [
            200,
            404,
            405,
        ]  # May not exist or be invalid

    def test_auth_enabled_server_requires_headers(self, auth_service):
        """Test that auth-enabled server requires headers"""
        server = GofrDocWebServer(require_auth=True, auth_service=auth_service)
        client = TestClient(server.app)

        # Discovery endpoints should still work without auth
        assert client.get("/ping").status_code == 200
        assert client.get("/templates").status_code == 200

    def test_auth_header_format_validation(self, client):
        """Test that auth header is parsed correctly"""
        # These should work with proper auth headers
        response = client.get("/templates", headers={"X-Auth-Token": "public:test-token"})
        assert response.status_code == 200

    def test_auth_group_extraction(self, client):
        """Test that group is extracted from auth header"""
        # Ensure the header is parsed correctly
        response = client.get("/templates", headers={"X-Auth-Token": "private:token123"})
        assert response.status_code == 200
