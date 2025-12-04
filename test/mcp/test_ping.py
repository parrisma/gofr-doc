#!/usr/bin/env python3
"""Test ping tool for MCP server using Streamable HTTP transport"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from app.logger import Logger, session_logger

# Port configuration via environment variables (defaults to production port)
MCP_PORT = os.environ.get("GOFR_DOC_MCP_PORT", "8011")
MCP_URL = f"http://localhost:{MCP_PORT}/mcp/"

# Note: auth_service and mcp_headers fixtures are now provided by conftest.py


@pytest.mark.asyncio
async def test_ping_tool_available(mcp_headers):
    """Test that ping tool is available in tool list"""
    logger: Logger = session_logger
    logger.info("Testing ping tool availability")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info("MCP server initialized successfully")

            # List tools to verify ping is available
            tools_result = await session.list_tools()
            tool_names = [tool.name for tool in tools_result.tools]
            logger.info("Found tools", count=len(tool_names), tools=tool_names)

            assert "ping" in tool_names, "ping tool not found"
            logger.info("Ping tool is available")


@pytest.mark.asyncio
async def test_ping_returns_correct_response(mcp_headers):
    """Test that ping tool returns timestamp and service info"""
    logger: Logger = session_logger
    logger.info("Testing ping tool response")

    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call ping tool
            result = await session.call_tool("ping", arguments={})

            # Verify response
            assert len(result.content) > 0, "No content returned from ping"
            text_content = result.content[0]
            assert hasattr(text_content, "text"), "Response is not text"

            response_text = text_content.text  # type: ignore
            assert "success" in response_text, "Missing 'success' status"
            assert "ok" in response_text, "Missing 'ok' status in response"
            assert "timestamp" in response_text.lower(), "Missing timestamp"
            assert (
                "Document generation service is online" in response_text
                or "online" in response_text.lower()
            ), "Missing service status message"

            logger.info("Ping tool returned correct response")
