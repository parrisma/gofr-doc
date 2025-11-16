#!/usr/bin/env python3
"""Test token expiry handling for both MCP and Web servers"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
import pytest
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from app.auth import AuthService
from app.logger import Logger, session_logger


# Test configuration
TEST_JWT_SECRET = "test-secret-key-for-auth-testing"
# Use the same token store as the running servers
SHARED_TOKEN_STORE = "/tmp/doco_test_tokens.json"
MCP_URL = "http://localhost:8011/mcp/"
WEB_URL = "http://localhost:8010"


@pytest.fixture
def auth_service():
    """Create an auth service for expiry tests that shares token store with running servers"""
    return AuthService(secret_key=TEST_JWT_SECRET, token_store_path=SHARED_TOKEN_STORE)


@pytest.mark.asyncio
async def test_expired_token_mcp(auth_service):
    """Test that MCP server rejects expired tokens

    NOTE: This test requires the MCP server to be running on localhost:8011
    """
    logger: Logger = session_logger
    logger.info("Testing MCP with expired token")

    # Check if MCP server is running (any response means it's up)
    async with httpx.AsyncClient() as client:
        try:
            ping = await client.post(f"{MCP_URL}ping", timeout=1.0)
            # Any HTTP response (200, 404, 406, etc.) means server is running
            logger.info("MCP server is running", status=ping.status_code)
        except (httpx.ConnectError, httpx.TimeoutException):
                pytest.skip("MCP server not running on localhost:8011")

    # Create token with 1 second expiry
    token = auth_service.create_token(group="test_group", expires_in_seconds=1)
    logger.info("Token created with 1-second expiry")

    # Wait for token to expire
    logger.info("Waiting 2 seconds for token to expire...")
    await asyncio.sleep(2)

    # Try to use expired token
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "render_graph",
                arguments={
                    "title": "Expiry Test",
                    "x": [1, 2, 3],
                    "y": [4, 5, 6],
                    "token": token,
                },
            )

            # Should get authentication error
            text_content = result.content[0]
            response_text = text_content.text  # type: ignore

            assert (
                "expired" in response_text.lower() or "authentication" in response_text.lower()
            ), f"Expected expiry error, got: {response_text}"

            logger.info("MCP correctly rejected expired token")

    # Cleanup
    auth_service.revoke_token(token)


@pytest.mark.asyncio
async def test_expired_token_web(auth_service):
    """Test that Web server rejects expired tokens

    NOTE: This test requires the web server to be running on localhost:8010
    """
    logger: Logger = session_logger
    logger.info("Testing Web with expired token")

    # Check if web server is running
    async with httpx.AsyncClient() as client:
        try:
            ping = await client.get(f"{WEB_URL}/ping", timeout=1.0)
            if ping.status_code != 200:
                pytest.skip("Web server not running on localhost:8010")
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip("Web server not running on localhost:8010")

    # Create token with 1 second expiry
    token = auth_service.create_token(group="test_group", expires_in_seconds=1)
    logger.info("Token created with 1-second expiry")

    # Wait for token to expire
    logger.info("Waiting 2 seconds for token to expire...")
    await asyncio.sleep(2)

    # Try to use expired token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{WEB_URL}/render",
            json={
                "title": "Expiry Test",
                "x": [1, 2, 3],
                "y": [4, 5, 6],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        logger.info("Web response with expired token", status=response.status_code)

        # Should get 401 Unauthorized
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

        response_data = response.json()
        assert (
            "expired" in response_data.get("detail", "").lower()
            or "authentication" in response_data.get("detail", "").lower()
        ), f"Expected expiry error, got: {response_data}"

        logger.info("Web correctly rejected expired token")

    # Cleanup
    auth_service.revoke_token(token)


@pytest.mark.asyncio
async def test_token_just_before_expiry(auth_service):
    """Test that token works just before expiry but fails after

    NOTE: This test requires the web server to be running on localhost:8010
    """
    logger: Logger = session_logger
    logger.info("Testing token boundary conditions")

    # Create token with 3 second expiry (more margin for test execution)
    token = auth_service.create_token(group="test_group", expires_in_seconds=3)

    # Check if web server is running
    async with httpx.AsyncClient() as client:
        try:
            ping = await client.get(f"{WEB_URL}/ping", timeout=1.0)
            if ping.status_code != 200:
                pytest.skip("Web server not running on localhost:8010")
        except (httpx.ConnectError, httpx.TimeoutException):
            pytest.skip("Web server not running on localhost:8010")

    # Use token immediately (should work)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{WEB_URL}/render",
            json={
                "title": "Boundary Test",
                "x": [1, 2],
                "y": [3, 4],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert (
            response.status_code == 200
        ), f"Token should work initially, got {response.status_code}"
        logger.info("Token works when fresh")

        # Wait for expiry (add extra second for test timing variance)
        await asyncio.sleep(3.5)

        # Try again (should fail)
        response = await client.post(
            f"{WEB_URL}/render",
            json={
                "title": "Boundary Test 2",
                "x": [1, 2],
                "y": [3, 4],
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 401, f"Token should be expired, got {response.status_code}"
        logger.info("Token rejected after expiry")

    # Cleanup
    auth_service.revoke_token(token)
