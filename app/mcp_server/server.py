"""Server lifecycle and StreamableHTTP wiring for MCP server."""

from __future__ import annotations

import contextlib
from typing import AsyncIterator

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from app.mcp_server.mcp_server import app, auth_service, initialize_server, logger


session_manager_http = StreamableHTTPSessionManager(
    app=app,
    event_store=None,
    json_response=False,
    stateless=False,
)


async def handle_streamable_http(scope, receive, send) -> None:
    await session_manager_http.handle_request(scope, receive, send)


@contextlib.asynccontextmanager
async def lifespan(starlette_app) -> AsyncIterator[None]:
    logger.info("Starting StreamableHTTP session manager")
    await initialize_server()
    async with session_manager_http.run():
        logger.info("StreamableHTTP session manager ready")
        yield


from gofr_common.web import (  # noqa: E402 - must import after MCP setup
    create_health_routes,
    create_mcp_starlette_app,
)


health_routes = create_health_routes(
    service="gofr-doc-mcp",
    auth_enabled=auth_service is not None,
)


starlette_app = create_mcp_starlette_app(
    mcp_handler=handle_streamable_http,
    lifespan=lifespan,
    env_prefix="GOFR_DOC",
    include_auth_middleware=True,
    additional_routes=health_routes,
)


async def main(host: str = "0.0.0.0", port: int = 8010) -> None:
    import uvicorn

    logger.info("Starting document MCP server", host=host, port=port)
    config = uvicorn.Config(starlette_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
