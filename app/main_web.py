import uvicorn
import argparse
import os
from app.web_server import DocoWebServer
from app.logger import Logger, session_logger
import sys

logger: Logger = session_logger

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="doco Web Server - Graph rendering REST API")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8010,
        help="Port number to listen on (default: 8010)",
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
    args = parser.parse_args()

    # Validate JWT secret if authentication is enabled
    jwt_secret = (
        args.jwt_secret
        or os.environ.get("DOCO_JWT_SECRET")
    )
    if not args.no_auth and not jwt_secret:
        logger.error(
            "FATAL: Authentication enabled but no JWT secret provided. Set DOCO_JWT_SECRET environment variable or use --jwt-secret flag, or use --no-auth to disable authentication"
        )
        sys.exit(1)

    # Initialize server with JWT configuration
    server = DocoWebServer(
        jwt_secret=jwt_secret, token_store_path=args.token_store, require_auth=not args.no_auth
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
