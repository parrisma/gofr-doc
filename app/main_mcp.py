import argparse
import os
import sys
import asyncio
from app.auth import AuthService
from app.logger import Logger, session_logger
from app.startup import validate_data_directory_structure

logger: Logger = session_logger

if __name__ == "__main__":
    # Validate data directory structure at startup
    try:
        validate_data_directory_structure(logger)
    except RuntimeError as e:
        logger.error("FATAL: Data directory validation failed", error=str(e))
        sys.exit(1)

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="doco MCP Server - Document rendering via Model Context Protocol"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("DOCO_MCP_PORT", "8011")),
        help="Port number to listen on (default: 8011, or DOCO_MCP_PORT env var)",
    )
    parser.add_argument(
        "--jwt-secret",
        type=str,
        default=None,
        help="JWT secret key (default: from DOCO_JWT_SECRET env var or auto-generated)",
    )
    parser.add_argument(
        "--token-store",
        type=str,
        default=None,
        help="Path to token store file (default: configured in app.config)",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Disable authentication (WARNING: insecure, for development only)",
    )
    parser.add_argument(
        "--templates-dir",
        type=str,
        default=None,
        help="Path to templates directory (default: app/templates)",
    )
    parser.add_argument(
        "--styles-dir",
        type=str,
        default=None,
        help="Path to styles directory (default: app/styles)",
    )
    args = parser.parse_args()

    # Create logger for startup messages
    startup_logger: Logger = session_logger

    # Validate JWT secret if authentication is enabled
    jwt_secret = args.jwt_secret or os.environ.get("DOCO_JWT_SECRET")
    if not args.no_auth and not jwt_secret:
        startup_logger.error(
            "FATAL: Authentication enabled but no JWT secret provided. Set DOCO_JWT_SECRET environment variable or use --jwt-secret flag, or use --no-auth to disable authentication"
        )
        sys.exit(1)

    # Initialize auth service only if auth is required
    auth_service = None
    if not args.no_auth:
        auth_service = AuthService(secret_key=jwt_secret, token_store_path=args.token_store)
        startup_logger.info("Authentication service initialized", jwt_enabled=True)
    else:
        startup_logger.info("Authentication disabled", jwt_enabled=False)

    # Import and configure mcp_server with auth service
    import app.mcp_server as mcp_server_module

    mcp_server_module.auth_service = auth_service
    mcp_server_module.templates_dir_override = args.templates_dir
    mcp_server_module.styles_dir_override = args.styles_dir
    from app.mcp_server import main

    try:
        startup_logger.info(
            "Starting MCP server",
            host=args.host,
            port=args.port,
            transport="Streamable HTTP",
            jwt_enabled=True,
        )
        asyncio.run(main(host=args.host, port=args.port))
        startup_logger.info("MCP server shutdown complete")
    except KeyboardInterrupt:
        startup_logger.info("Shutdown complete")
        sys.exit(0)
    except Exception as e:
        startup_logger.error("Failed to start server", error=str(e), error_type=type(e).__name__)
        sys.exit(1)
