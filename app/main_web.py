import uvicorn
import argparse
import os
import sys
from app.web_server.web_server import GofrDocWebServer
from gofr_common.auth import (
    AuthService,
    GroupRegistry,
    JwtSecretProvider,
    create_stores_from_env,
    create_vault_client_from_env,
)
from app.logger import Logger, session_logger
import app.startup.validation

logger: Logger = session_logger

if __name__ == "__main__":
    # Validate data directory structure at startup
    try:
        app.startup.validation.validate_data_directory_structure(logger)
    except RuntimeError as e:
        logger.error("FATAL: Data directory validation failed", error=str(e))
        sys.exit(1)

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="gofr-doc Web Server - Document rendering REST API"
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
        default=int(os.environ.get("GOFR_DOC_WEB_PORT", "8012")),
        help="Port number to listen on (default: 8012, or GOFR_DOC_WEB_PORT env var)",
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
        help="Path to templates directory (default: data/templates).",
    )
    parser.add_argument(
        "--fragments-dir",
        type=str,
        default=None,
        help="Path to fragments directory (default: data/fragments).",
    )
    parser.add_argument(
        "--styles-dir",
        type=str,
        default=None,
        help="Path to styles directory (default: data/styles).",
    )
    args = parser.parse_args()

    # Initialize AuthService if authentication is enabled
    auth_service = None
    if not args.no_auth:
        vault_client = create_vault_client_from_env("GOFR_DOC", logger=logger)
        secret_provider = JwtSecretProvider(
            vault_client=vault_client,
            logger=logger,
        )
        token_store, group_store = create_stores_from_env(
            "GOFR_DOC",
            vault_client=vault_client,
        )
        group_registry = GroupRegistry(store=group_store)
        auth_service = AuthService(
            token_store=token_store,
            group_registry=group_registry,
            secret_provider=secret_provider,
            env_prefix="GOFR_DOC",
        )
        logger.info(
            "Authentication service initialized",
            jwt_enabled=True,
            backend=type(token_store).__name__,
        )
    else:
        logger.warning(
            "Authentication DISABLED - running in no-auth mode (INSECURE)",
            jwt_enabled=False,
        )

    # Initialize server
    # Note: AuthService is injected for token verification
    # Create web server instance
    server = GofrDocWebServer(
        templates_dir=args.templates_dir,
        fragments_dir=args.fragments_dir,
        styles_dir=args.styles_dir,
        require_auth=not args.no_auth,
        auth_service=auth_service,
    )

    try:
        logger.info("=" * 70)
        logger.info("STARTING GOFR_DOC WEB SERVER (REST API)")
        logger.info("=" * 70)
        logger.info(
            "Configuration",
            host=args.host,
            port=args.port,
            transport="HTTP REST API",
            jwt_enabled=not args.no_auth,
            templates_dir=args.templates_dir or "(default)",
            fragments_dir=args.fragments_dir or "(default)",
            styles_dir=args.styles_dir or "(default)",
        )
        logger.info("=" * 70)
        logger.info(f"API endpoint: http://{args.host}:{args.port}")
        logger.info(f"API documentation: http://{args.host}:{args.port}/docs")
        logger.info(f"Health check: http://{args.host}:{args.port}/ping")
        logger.info("=" * 70)
        uvicorn.run(server.app, host=args.host, port=args.port, log_level="info")
        logger.info("=" * 70)
        logger.info("Web server shutdown complete")
        logger.info("=" * 70)
    except KeyboardInterrupt:
        logger.info("Web server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Failed to start web server", error=str(e), error_type=type(e).__name__)
        sys.exit(1)
