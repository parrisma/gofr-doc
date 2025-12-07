#!/usr/bin/env python3
"""
Test script for the web server functionality.
Tests the FastAPI endpoints for graph rendering.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to enable imports when run directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from httpx import AsyncClient, ASGITransport
from app.logger import Logger, session_logger
from app.web_server.web_server import GofrDocWebServer
from app.auth import AuthService


async def test_web_server():
    """Test the web server endpoints"""

    logger: Logger = session_logger

    # Create server instance with auth
    server = GofrDocWebServer(
        auth_service=None,
        require_auth=False,
    )
    app = server.app

    # Create auth service and token for testing
    auth_service = AuthService(
        secret_key="test-secret-key", token_store_path="/tmp/manual_test_tokens.json"
    )
    token = auth_service.create_token(group="test_group")
    logger.info("Created test token", token=token[:20] + "...")

    logger.info("Starting web server tests")
    print("-" * 50)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {token}"}
    ) as client:

        # Test 1: Line chart with base64 response
        print("\n" + "-" * 50)
        logger.info("Testing line chart with base64 response")
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
        logger.info("Line chart test passed", response_has_image=True)

        # Test 2: Bar chart with direct image response
        print("\n" + "-" * 50)
        logger.info("Testing bar chart with direct image response")
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
        logger.info("Bar chart test passed", content_length=len(response.content))

        # Test 3: Scatter plot
        print("\n" + "-" * 50)
        logger.info("Testing scatter plot")
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
        logger.info("Scatter plot test passed")

        # Test 4: Dark theme
        print("\n" + "-" * 50)
        logger.info("Testing dark theme")
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
        logger.info("Dark theme test passed")

        # Test 5: Light theme (explicit)
        print("\n" + "-" * 50)
        logger.info("Testing light theme")
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
        logger.info("Light theme test passed")

        # Test 6: SVG format
        print("\n" + "-" * 50)
        logger.info("Testing SVG format")
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
        logger.info("SVG format test passed")

        # Test 7: PDF format
        print("\n" + "-" * 50)
        logger.info("Testing PDF format")
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
        logger.info("PDF format test passed")

        # Test 8: Custom styling
        print("\n" + "-" * 50)
        logger.info("Testing custom styling")
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
        logger.info("Custom styling test passed")

        # Test 9: Validation - mismatched arrays
        print("\n" + "-" * 50)
        logger.info("Testing validation for mismatched arrays")
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
        logger.info(
            "Validation correctly caught mismatched arrays",
            error_count=len(error_data["detail"]["errors"]),
        )

        # Test 10: Validation - invalid chart type
        print("\n" + "-" * 50)
        logger.info("Testing validation for invalid chart type")
        response = await client.post(
            "/render",
            json={"title": "Invalid Type", "x": [1, 2, 3], "y": [1, 2, 3], "type": "invalid_type"},
        )
        assert response.status_code == 400
        error_data = response.json()
        assert "suggestions" in str(error_data)
        logger.info("Validation correctly caught invalid chart type")

        # Test 11: Validation - empty arrays
        print("\n" + "-" * 50)
        logger.info("Testing validation for empty arrays")
        response = await client.post(
            "/render", json={"title": "Empty Data", "x": [], "y": [], "type": "line"}
        )
        assert response.status_code == 400
        error_data = response.json()
        logger.info("Validation correctly caught empty arrays")

        # Test 12: Validation - invalid alpha value
        print("\n" + "-" * 50)
        logger.info("Testing validation for invalid alpha")
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

        # Test 13: Validation - invalid color format
        print("\n" + "-" * 50)
        logger.info("Testing validation for invalid color")
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

    # Cleanup: revoke the test token
    auth_service.revoke_token(token)
    logger.info("Test token revoked")

    print("\n" + "=" * 50)
    logger.info("All web server tests completed successfully")
    print("=" * 50)


def main():
    """Run the tests"""
    logger: Logger = session_logger

    try:
        asyncio.run(test_web_server())
    except KeyboardInterrupt:
        logger.warning("Test interrupted by user")
    except AssertionError as e:
        logger.error("Test assertion failed", error=str(e))
        import traceback

        traceback.print_exc()
        exit(1)
    except Exception as e:
        logger.error("Test failed", error=str(e))
        import traceback

        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
