#!/usr/bin/env python3
"""
Quick script to discover MCP server capabilities from the command line.
Run this to see what tools the MCP server exposes.
"""

import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def discover_mcp_server():
    """Connect to MCP server and list all available tools"""

    http_url = "http://localhost:8011/mcp/"

    print("=" * 60)
    print("MCP SERVER DISCOVERY")
    print("=" * 60)
    print(f"\nConnecting to: {http_url}")
    print()

    async with streamablehttp_client(http_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            print("Connected successfully\n")

            # Get server info
            print("-" * 60)
            print("SERVER INFORMATION")
            print("-" * 60)
            print(f"Server: doco-renderer")
            print(f"Version: 1.0.0")
            print(f"Transport: Streamable HTTP")
            print()

            # List available tools
            tools_result = await session.list_tools()

            print("-" * 60)
            print(f"AVAILABLE TOOLS ({len(tools_result.tools)})")
            print("-" * 60)

            for i, tool in enumerate(tools_result.tools, 1):
                print(f"\n{i}. {tool.name}")
                print(f"   Description: {tool.description}")

                if hasattr(tool, "inputSchema") and tool.inputSchema:
                    schema = tool.inputSchema

                    # Show required parameters
                    if "required" in schema:
                        print(f"   Required: {', '.join(schema['required'])}")

                    # Show all parameters
                    if "properties" in schema:
                        print(f"   Parameters:")
                        for param_name, param_info in schema["properties"].items():
                            param_type = param_info.get("type", "unknown")
                            param_desc = param_info.get("description", "No description")
                            is_required = param_name in schema.get("required", [])
                            req_marker = " [REQUIRED]" if is_required else " [optional]"

                            print(f"      • {param_name} ({param_type}){req_marker}")
                            print(f"        {param_desc}")

                            # Show enum values if present
                            if "enum" in param_info:
                                print(f"        Allowed values: {', '.join(param_info['enum'])}")

                            # Show default if present
                            if "default" in param_info:
                                print(f"        Default: {param_info['default']}")

            print("\n" + "=" * 60)
            print("ENDPOINT INFORMATION")
            print("=" * 60)
            print(f"Streamable HTTP Endpoint: http://localhost:8011/mcp/")
            print(f"For N8N: http://doco_dev:8011/mcp/ (on doco_net)")
            print(f"For Host: http://localhost:8011/mcp/")
            print(f"Transport: Streamable HTTP (modern MCP standard)")
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(discover_mcp_server())
