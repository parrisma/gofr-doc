import uvicorn
import argparse
import os
from app.web_server import DocoWebServer
from app.logger import Logger, session_logger
from app.startup import validate_data_directory_structure
import sys

logger: Logger = session_logger

if __name__ == "__main__":
    # Validate data directory structure at startup
    try:
        validate_data_directory_structure(logger)
    except RuntimeError as e:
        logger.error("FATAL: Data directory validation failed", error=str(e))
        sys.exit(1)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="doco Web Server - Document rendering REST API")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("DOCO_WEB_PORT", "8010")),
        help="Port number to listen on (default: 8010, or DOCO_WEB_PORT env var)",
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
        help="Path to templates directory (default: data/docs/templates)",
    )
    parser.add_argument(
        "--fragments-dir",
        type=str,
        default=None,
        help="Path to fragments directory (default: data/docs/fragments)",
    )
    parser.add_argument(
        "--styles-dir",
        type=str,
        default=None,
        help="Path to styles directory (default: data/docs/styles)",
    )
    args = parser.parse_args()

    # Validate JWT secret if authentication is enabled
    jwt_secret = args.jwt_secret or os.environ.get("DOCO_JWT_SECRET")
    if not args.no_auth and not jwt_secret:
        logger.error(
            "FATAL: Authentication enabled but no JWT secret provided. Set DOCO_JWT_SECRET environment variable or use --jwt-secret flag, or use --no-auth to disable authentication"
        )
        sys.exit(1)

    # Initialize server
    # Note: Authentication is handled via X-Auth-Token header (group:token format)
    server = DocoWebServer(
        templates_dir=args.templates_dir,
        fragments_dir=args.fragments_dir,
        styles_dir=args.styles_dir,
        require_auth=not args.no_auth,
    )

    try:
        logger.info(
            "Starting web server",
            host=args.host,
            port=args.port,
            transport="HTTP REST API",
            jwt_enabled=not args.no_auth,
        )
        uvicorn.run(server.app, host=args.host, port=args.port)
        logger.info("Web server shutdown complete")
    except KeyboardInterrupt:
        logger.info("Web server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Failed to start web server", error=str(e), error_type=type(e).__name__)
        sys.exit(1)
