#!/usr/bin/env python3
"""
Test web server rendering functionality with pytest.
Tests various chart types, formats, themes, and validation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from httpx import AsyncClient, ASGITransport
from app.logger import Logger, session_logger
from app.web_server import DocoWebServer
from app.auth import TokenInfo, verify_token
from datetime import datetime, timedelta


def mock_verify_token():
    """Mock token verification for testing without authentication"""
    return TokenInfo(
        token="mock-token",
        group="test-group",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        issued_at=datetime.utcnow(),
    )


@pytest.fixture
def server():
    """Create a GraphWebServer instance"""
    return DocoWebServer(jwt_secret="test-secret-for-unit-tests")


@pytest.fixture
def app(server):
    """Get the FastAPI app from the server with auth dependency overridden"""
    # Override the verify_token dependency to bypass authentication in tests
    server.app.dependency_overrides[verify_token] = mock_verify_token
    return server.app


@pytest.mark.asyncio
async def test_render_line_chart_base64(app):
    """Test rendering line chart with base64 response"""
    logger: Logger = session_logger
    logger.info("Testing line chart with base64 response")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Test Line Chart",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10],
                "xlabel": "X Axis",
                "ylabel": "Y Axis",
                "type": "line",
                "return_base64": True,
            },
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "image" in data, "Response should contain 'image' key"
        logger.info("Line chart with base64 passed")


@pytest.mark.asyncio
async def test_render_bar_chart_direct_image(app):
    """Test rendering bar chart with direct image response"""
    logger: Logger = session_logger
    logger.info("Testing bar chart with direct image response")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Test Bar Chart",
                "x": [1, 2, 3, 4, 5],
                "y": [5, 8, 3, 7, 4],
                "type": "bar",
                "return_base64": False,
                "format": "png",
            },
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.headers["content-type"] == "image/png"
        assert len(response.content) > 0, "Image content should not be empty"
        logger.info("Bar chart with direct image passed")


@pytest.mark.asyncio
async def test_render_scatter_plot(app):
    """Test rendering scatter plot"""
    logger: Logger = session_logger
    logger.info("Testing scatter plot")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Test Scatter Plot",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 5, 3, 8, 6],
                "type": "scatter",
                "marker_size": 50,
                "color": "red",
                "return_base64": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "image" in data
        logger.info("Scatter plot passed")


@pytest.mark.asyncio
async def test_render_dark_theme(app):
    """Test rendering with dark theme"""
    logger: Logger = session_logger
    logger.info("Testing dark theme")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Dark Theme Chart",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10],
                "type": "line",
                "theme": "dark",
                "return_base64": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "image" in data
        logger.info("Dark theme passed")


@pytest.mark.asyncio
async def test_render_light_theme(app):
    """Test rendering with light theme (explicit)"""
    logger: Logger = session_logger
    logger.info("Testing light theme")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Light Theme Chart",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10],
                "type": "line",
                "theme": "light",
                "return_base64": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "image" in data
        logger.info("Light theme passed")


@pytest.mark.asyncio
async def test_render_svg_format(app):
    """Test rendering SVG format"""
    logger: Logger = session_logger
    logger.info("Testing SVG format")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "SVG Chart",
                "x": [1, 2, 3],
                "y": [1, 4, 9],
                "type": "line",
                "format": "svg",
                "return_base64": False,
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        logger.info("SVG format passed")


@pytest.mark.asyncio
async def test_render_pdf_format(app):
    """Test rendering PDF format"""
    logger: Logger = session_logger
    logger.info("Testing PDF format")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "PDF Chart",
                "x": [1, 2, 3],
                "y": [1, 4, 9],
                "type": "bar",
                "format": "pdf",
                "return_base64": False,
            },
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        logger.info("PDF format passed")


@pytest.mark.asyncio
async def test_render_custom_styling(app):
    """Test rendering with custom styling options"""
    logger: Logger = session_logger
    logger.info("Testing custom styling")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Custom Styled Chart",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10],
                "type": "line",
                "color": "#FF5733",
                "line_width": 3.0,
                "alpha": 0.7,
                "return_base64": True,
            },
        )

        assert response.status_code == 200
        logger.info("Custom styling passed")


@pytest.mark.asyncio
async def test_validation_mismatched_arrays(app):
    """Test validation catches mismatched array lengths"""
    logger: Logger = session_logger
    logger.info("Testing validation for mismatched arrays")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Bad Chart",
                "x": [1, 2, 3],
                "y": [1, 2],  # Mismatched length
                "type": "line",
            },
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        error_data = response.json()
        assert "errors" in error_data["detail"]
        assert len(error_data["detail"]["errors"]) > 0
        logger.info("Validation correctly caught mismatched arrays")


@pytest.mark.asyncio
async def test_validation_invalid_chart_type(app):
    """Test validation catches invalid chart type"""
    logger: Logger = session_logger
    logger.info("Testing validation for invalid chart type")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={"title": "Invalid Type", "x": [1, 2, 3], "y": [1, 2, 3], "type": "invalid_type"},
        )

        assert response.status_code == 400
        error_data = response.json()
        assert "suggestions" in str(error_data)
        logger.info("Validation correctly caught invalid chart type")


@pytest.mark.asyncio
async def test_validation_empty_arrays(app):
    """Test validation catches empty data arrays"""
    logger: Logger = session_logger
    logger.info("Testing validation for empty arrays")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={"title": "Empty Data", "x": [], "y": [], "type": "line"},
        )

        assert response.status_code == 400
        error_data = response.json()
        logger.info("Validation correctly caught empty arrays")


@pytest.mark.asyncio
async def test_validation_invalid_alpha(app):
    """Test validation catches invalid alpha value"""
    logger: Logger = session_logger
    logger.info("Testing validation for invalid alpha")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Bad Alpha",
                "x": [1, 2, 3],
                "y": [1, 2, 3],
                "alpha": 2.5,  # Out of range
            },
        )

        assert response.status_code == 400
        error_data = response.json()
        logger.info("Validation correctly caught invalid alpha value")


@pytest.mark.asyncio
async def test_validation_invalid_color(app):
    """Test validation catches invalid color format"""
    logger: Logger = session_logger
    logger.info("Testing validation for invalid color")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Bad Color",
                "x": [1, 2, 3],
                "y": [1, 2, 3],
                "color": "not_a_valid_color_123",
            },
        )

        assert response.status_code == 400
        error_data = response.json()
        logger.info("Validation correctly caught invalid color format")
