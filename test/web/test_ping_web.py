#!/usr/bin/env python3
"""Test ping endpoint for web server (web-specific filename to avoid import-name collision)

This file was renamed from test_ping.py to avoid import filename collisions with
the MCP test suite which also had a test_ping.py module.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from fastapi.testclient import TestClient
from app.web_server.web_server import GofrDocWebServer


@pytest.fixture
def client(test_data_dir, auth_service):
    """Create a TestClient for the web server."""
    server = GofrDocWebServer(auth_service=auth_service)
    return TestClient(server.app)


def test_ping_endpoint_returns_200(client):
    """Test that ping endpoint returns 200 status"""
    response = client.get("/ping")
    assert response.status_code == 200


def test_ping_endpoint_returns_ok_status(client):
    """Test that ping endpoint returns 'ok' status"""
    response = client.get("/ping")
    data = response.json()

    assert "status" in data
    assert data["status"] == "ok"


def test_ping_endpoint_returns_timestamp(client):
    """Test that ping endpoint returns a timestamp"""
    response = client.get("/ping")
    data = response.json()

    assert "timestamp" in data
    assert isinstance(data["timestamp"], str)
    assert len(data["timestamp"]) > 0


def test_ping_endpoint_returns_service_name(client):
    """Test that ping endpoint returns service identifier"""
    response = client.get("/ping")
    data = response.json()

    assert "service" in data
    assert data["service"] == "gofr-doc"
