#!/usr/bin/env python3
"""Document generation MCP server with group-based security.

This server implements the Model Context Protocol (MCP) for document generation with
group-based access control.

Security Model:
- JWT Authentication: Bearer tokens with {"group": "...", "exp": ..., "iat": ...}
- Group Isolation: Sessions, templates, styles, and fragments are isolated by group
- Session Verification: All operations verify session.group == caller_group
- Discovery Tools: list_templates, get_template_details, etc. do NOT require authentication

Authentication Flow:
1. Client sends JWT token in Authorization: Bearer header
2. verify_auth() extracts and validates token -> returns (auth_group, error)
3. handle_call_tool() injects auth_group into tool arguments
4. Tool handlers verify session.group == auth_group before operations
5. Generic "SESSION_NOT_FOUND" errors prevent information leakage across groups
"""

from __future__ import annotations

import sys
from pathlib import Path as SysPath
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import Tool

# Ensure project root is on the import path when running directly
sys.path.insert(0, str(SysPath(__file__).parent.parent))

from app.auth import AuthService  # noqa: E402
from app.logger import Logger, session_logger  # noqa: E402

from app.mcp_server import runtime_settings  # noqa: E402
from app.mcp_server.components import initialize_components  # noqa: E402
from app.mcp_server import routing  # noqa: E402
from app.mcp_server.state import set_components  # noqa: E402
from app.mcp_server.tool_schemas import build_tools  # noqa: E402
from app.mcp_server.tool_types import ToolResponse  # noqa: E402


app = Server("gofr-doc-document-service")
logger: Logger = session_logger

auth_service: Optional[AuthService] = None  # Injected by entrypoint


async def initialize_server() -> None:
    """Initialize server components."""
    logger.info("Initialising document MCP server")

    comps = initialize_components(
        templates_dir_override=runtime_settings.templates_dir_override,
        styles_dir_override=runtime_settings.styles_dir_override,
        logger=logger,
    )
    set_components(comps)


@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    return await build_tools()


@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> ToolResponse:
    return await routing.dispatch_tool_call(
        name=name,
        arguments=arguments,
        auth_service=auth_service,
        logger=logger,
    )
