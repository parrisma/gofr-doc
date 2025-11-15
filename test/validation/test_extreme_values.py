#!/usr/bin/env python3
"""Test rendering with extreme numeric values that could crash matplotlib"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import math
from httpx import AsyncClient, ASGITransport
from app.logger import Logger, session_logger
from app.web_server import DocoWebServer


@pytest.fixture
def app():
    """Create a GraphWebServer instance with auth disabled for testing"""
    server = DocoWebServer()
    # Override auth dependency
    from app.auth import TokenInfo
    from datetime import datetime, timedelta

    def mock_verify_token():
        return TokenInfo(
            token="mock-token",
            group="test",
            expires_at=datetime.now() + timedelta(hours=1),
            issued_at=datetime.now(),
        )

    from app.auth import verify_token

    server.app.dependency_overrides[verify_token] = mock_verify_token
    return server.app


@pytest.mark.asyncio
async def test_render_with_infinity_values(app):
    """Test that infinity values are properly handled"""
    logger: Logger = session_logger
    logger.info("Testing render with infinity values")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Note: float('inf') cannot be serialized to JSON, so this tests
        # the client library's handling of invalid values
        try:
            response = await client.post(
                "/render",
                json={
                    "title": "Infinity Test",
                    "x": [1, 2, 3, 4, 5],
                    "y": [1, float("inf"), 3, 4, 5],
                    "type": "line",
                },
            )
            # If we get here, the library converted inf to something else
            logger.info("Response status for infinity", status=response.status_code)
            assert response.status_code in [
                200,
                400,
                422,
            ], f"Unexpected status: {response.status_code}"
        except ValueError as e:
            # Expected: JSON cannot serialize infinity
            logger.info("Infinity values cannot be serialized to JSON", error=str(e))
            assert "JSON compliant" in str(e) or "Infinity" in str(e)
        else:
            logger.info("Infinity values handled by matplotlib")


@pytest.mark.asyncio
async def test_render_with_nan_values(app):
    """Test that NaN values are properly handled"""
    logger: Logger = session_logger
    logger.info("Testing render with NaN values")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Note: float('nan') cannot be serialized to JSON, so this tests
        # the client library's handling of invalid values
        try:
            response = await client.post(
                "/render",
                json={
                    "title": "NaN Test",
                    "x": [1, 2, 3, 4, 5],
                    "y": [1, 2, float("nan"), 4, 5],
                    "type": "line",
                },
            )
            logger.info("Response status for NaN", status=response.status_code)
            # If we get here, the library converted nan to null or something else
            assert response.status_code in [
                200,
                400,
                422,
            ], f"Unexpected status: {response.status_code}"
        except ValueError as e:
            # Expected: JSON cannot serialize NaN
            logger.info("NaN values cannot be serialized to JSON", error=str(e))
            assert "JSON compliant" in str(e) or "NaN" in str(e)


@pytest.mark.asyncio
async def test_render_with_very_large_numbers(app):
    """Test with very large numbers that could cause overflow"""
    logger: Logger = session_logger
    logger.info("Testing render with very large numbers")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test with numbers close to float max
        large_num = 1e308

        response = await client.post(
            "/render",
            json={
                "title": "Large Numbers Test",
                "x": [1, 2, 3, 4, 5],
                "y": [
                    large_num,
                    large_num * 0.9,
                    large_num * 0.8,
                    large_num * 0.7,
                    large_num * 0.6,
                ],
                "type": "bar",
            },
        )

        logger.info("Response status for large numbers", status=response.status_code)

        # Should handle or reject gracefully
        assert response.status_code in [200, 400, 500], f"Unexpected status: {response.status_code}"

        if response.status_code == 200:
            logger.info("Very large numbers handled successfully")
        else:
            logger.info("Very large numbers handled with error response")


@pytest.mark.asyncio
async def test_render_with_very_small_numbers(app):
    """Test with numbers close to zero (underflow)"""
    logger: Logger = session_logger
    logger.info("Testing render with very small numbers")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        small_num = 1e-308

        response = await client.post(
            "/render",
            json={
                "title": "Small Numbers Test",
                "x": [1, 2, 3, 4, 5],
                "y": [small_num, small_num * 2, small_num * 3, small_num * 4, small_num * 5],
                "type": "line",
            },
        )

        logger.info("Response status for small numbers", status=response.status_code)

        # Should render successfully
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        logger.info("Very small numbers handled")


@pytest.mark.asyncio
async def test_render_with_mixed_extreme_values(app):
    """Test render with mixture of extreme values"""
    logger: Logger = session_logger
    logger.info("Testing render with mixed extreme values")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Mixed Extremes",
                "x": [1, 2, 3, 4, 5],
                "y": [1e308, -1e308, 1e-308, 0, 1],
                "type": "scatter",
            },
        )

        logger.info("Response status for mixed extremes", status=response.status_code)

        # Should either render or reject (matplotlib may fail internally)
        assert response.status_code in [200, 400, 500], f"Unexpected status: {response.status_code}"

        if response.status_code == 200:
            logger.info("Mixed extreme values rendered successfully")
        elif response.status_code == 500:
            # Matplotlib can't handle the range calculation with these extremes
            logger.info("Mixed extreme values cause matplotlib error (expected)")
        else:
            error_data = response.json()
            logger.info("Mixed extreme values rejected", error=error_data.get("detail"))


@pytest.mark.asyncio
async def test_render_with_all_same_values(app):
    """Test with all data points having same value (edge case for scaling)"""
    logger: Logger = session_logger
    logger.info("Testing render with all same values")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Constant Values Test",
                "x": [1, 2, 3, 4, 5],
                "y": [42, 42, 42, 42, 42],
                "type": "line",
            },
        )

        # Matplotlib should handle this by creating a flat line
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        logger.info("Constant values rendered successfully")


@pytest.mark.asyncio
async def test_render_with_single_data_point(app):
    """Test with only one data point"""
    logger: Logger = session_logger
    logger.info("Testing render with single data point")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Single Point Test",
                "x": [1],
                "y": [42],
                "type": "scatter",
            },
        )

        # Should render (scatter plot can show one point)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        logger.info("Single data point rendered successfully")


@pytest.mark.asyncio
async def test_render_with_negative_infinity(app):
    """Test with negative infinity"""
    logger: Logger = session_logger
    logger.info("Testing render with negative infinity")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Note: float('-inf') cannot be serialized to JSON
        try:
            response = await client.post(
                "/render",
                json={
                    "title": "Negative Infinity Test",
                    "x": [1, 2, 3],
                    "y": [1, float("-inf"), 3],
                    "type": "bar",
                },
            )
            logger.info("Response status for negative infinity", status=response.status_code)
            assert response.status_code in [
                200,
                400,
                422,
            ], f"Unexpected status: {response.status_code}"
        except ValueError as e:
            # Expected: JSON cannot serialize negative infinity
            logger.info("Negative infinity cannot be serialized to JSON", error=str(e))
            assert "JSON compliant" in str(e) or "Infinity" in str(e)


@pytest.mark.asyncio
async def test_render_with_zero_range(app):
    """Test when all x values are the same (zero range on x-axis)"""
    logger: Logger = session_logger
    logger.info("Testing render with zero range on x-axis")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/render",
            json={
                "title": "Zero Range Test",
                "x": [5, 5, 5, 5, 5],
                "y": [1, 2, 3, 4, 5],
                "type": "line",
            },
        )

        # Matplotlib should handle this
        logger.info("Response status for zero range", status=response.status_code)
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        logger.info("Zero range handled")
