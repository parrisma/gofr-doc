#!/usr/bin/env python3
"""
Test script for proxy mode functionality

Tests:
1. Render with proxy mode and get GUID
2. Retrieve image using get_image MCP tool
3. Test GUID storage and retrieval
4. Test invalid GUID handling
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from app.logger import Logger, session_logger


MCP_URL = "http://localhost:8011/mcp/"


@pytest.mark.asyncio
async def test_render_with_proxy_mode_returns_guid(test_jwt_token):
    """Test proxy mode end-to-end"""
    logger: Logger = session_logger
    logger.info("Starting proxy mode tests")

    http_url = "http://localhost:8011/mcp/"

    async with streamablehttp_client(http_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info("MCP session initialized")

            # Test 1: Render graph with proxy mode
            logger.info("Test 1: Rendering graph with proxy=true")
            render_args = {
                "title": "Proxy Mode Test",
                "x": [1, 2, 3, 4, 5],
                "y": [10, 20, 15, 25, 20],
                "type": "line",
                "format": "png",
                "proxy": True,
                "token": test_jwt_token,
            }

            result = await session.call_tool("render_graph", render_args)

            # Extract GUID from response
            text_content = result.content[0]
            assert hasattr(text_content, "text"), "Expected text response"
            response_text = text_content.text  # type: ignore

            # Parse GUID from response
            guid = None
            for line in response_text.split("\n"):
                if "GUID:" in line:
                    guid = line.split("GUID:")[1].strip()
                    break

            assert guid is not None, "No GUID found in response"
            logger.info(f"Graph rendered with GUID: {guid}")

            # Test 2: Retrieve image using get_image tool
            logger.info("Test 2: Retrieving image by GUID")
            get_args = {"guid": guid, "token": test_jwt_token}

            result = await session.call_tool("get_image", get_args)

            # Verify we got an image back
            assert len(result.content) >= 1, "No content in response"

            image_found = False
            for content in result.content:
                if hasattr(content, "type") and content.type == "image":
                    image_found = True
                    assert hasattr(content, "data"), "Image content has no data"
                    assert len(content.data) > 0, "Image data is empty"
                    logger.info(f"Image retrieved successfully (size: {len(content.data)} chars)")
                    break

            assert image_found, "No image content in response"

            # Test 3: Try to retrieve non-existent GUID
            logger.info("Test 3: Testing invalid GUID handling")
            invalid_guid = "00000000-0000-0000-0000-000000000000"
            get_args = {"guid": invalid_guid, "token": test_jwt_token}

            result = await session.call_tool("get_image", get_args)

            # Should get error message
            text_content = result.content[0]
            assert hasattr(text_content, "text"), "Expected text response"
            assert "not found" in text_content.text.lower(), "Expected 'not found' error"  # type: ignore
            logger.info("Invalid GUID correctly handled")

            # Test 4: Render with SVG format
            logger.info("Test 4: Rendering graph with SVG format")
            svg_args = {
                "title": "SVG Format Test",
                "x": [1, 2, 3],
                "y": [7, 8, 9],
                "format": "svg",
                "proxy": True,
            }

            result = await session.call_tool("render_graph", svg_args)
            text_content = result.content[0]
            assert hasattr(text_content, "text"), "Expected text response"
            response_text = text_content.text  # type: ignore

            # Check for .svg extension in the GUID
            if ".svg" in response_text.lower():
                logger.info("SVG format response received with .svg extension")
            else:
                logger.info(f"Response: {response_text[:100]}")

            logger.info("=" * 60)
            logger.info("All proxy mode tests passed!")
            logger.info("=" * 60)
