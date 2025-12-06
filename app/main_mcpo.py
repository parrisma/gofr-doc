#!/usr/bin/env python3
"""MCPO wrapper entry point for gofr_doc MCP server

This script starts an MCPO proxy that exposes the gofr_doc MCP server
as OpenAPI-compatible HTTP endpoints for Open WebUI integration.
"""

import argparse
import os
import signal
import sys

from app.logger import Logger, session_logger
from app.mcpo.wrapper import start_mcpo_wrapper

logger: Logger = session_logger


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Received shutdown signal", signal=signum)
    sys.exit(0)


if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="gofr_doc MCPO Wrapper - Expose MCP server as OpenAPI endpoints"
    )
    parser.add_argument(
        "--mcp-host",
        type=str,
        default="localhost",
        help="Host where MCP server is running (default: localhost)",
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=int(os.environ.get("GOFR_DOC_MCP_PORT", "8010")),
        help="Port where MCP server is listening (default: 8010)",
    )
    parser.add_argument(
        "--mcpo-port",
        type=int,
        default=int(os.environ.get("GOFR_DOC_MCPO_PORT", "8011")),
        help="Port for MCPO proxy to listen on (default: 8011)",
    )
    parser.add_argument(
        "--mcpo-host",
        type=str,
        default=os.environ.get("GOFR_DOC_MCPO_HOST", "0.0.0.0"),
        help="Host for MCPO proxy to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API key for Open WebUI -> MCPO authentication (default: from GOFR_DOC_MCPO_API_KEY env or 'changeme')",
    )
    parser.add_argument(
        "--auth-token",
        type=str,
        default=None,
        help="JWT token for MCPO -> MCP authentication (default: from GOFR_DOC_JWT_TOKEN env)",
    )
    parser.add_argument(
        "--auth",
        action="store_true",
        help="Enable authenticated mode (requires --auth-token or GOFR_DOC_JWT_TOKEN)",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Disable authentication (public mode, default)",
    )

    args = parser.parse_args()

    # Determine auth mode
    use_auth = False
    if args.auth:
        use_auth = True
    elif args.no_auth:
        use_auth = False
    else:
        # Check environment variable
        mode = os.environ.get("GOFR_DOC_MCPO_MODE", "public").lower()
        use_auth = mode == "auth"

    # Validate auth requirements
    auth_token = args.auth_token or os.environ.get("GOFR_DOC_JWT_TOKEN")
    if use_auth and not auth_token:
        logger.error("ERROR: --auth-token or GOFR_DOC_JWT_TOKEN required for authenticated mode")
        sys.exit(1)

    mode_str = "AUTHENTICATED" if use_auth else "PUBLIC (NO AUTH)"

    # Startup banner
    logger.info("=" * 70)
    logger.info("STARTING GOFR_DOC MCPO WRAPPER (OpenAPI Proxy)")
    logger.info("=" * 70)
    logger.info(
        "Configuration",
        mode=mode_str,
        mcp_endpoint=f"http://{args.mcp_host}:{args.mcp_port}/mcp",
        mcpo_host=args.mcpo_host,
        mcpo_port=args.mcpo_port,
        has_auth_token=bool(auth_token),
        has_api_key=bool(args.api_key),
    )
    logger.info("=" * 70)

    wrapper = None
    try:
        # Start MCPO wrapper
        logger.info(
            "🔌 Connecting to MCP server...", mcp_url=f"http://{args.mcp_host}:{args.mcp_port}/mcp"
        )
        wrapper = start_mcpo_wrapper(
            mcp_host=args.mcp_host,
            mcp_port=args.mcp_port,
            mcpo_host=args.mcpo_host,
            mcpo_port=args.mcpo_port,
            mcpo_api_key=args.api_key,
            auth_token=auth_token,
            use_auth=use_auth,
        )

        logger.info("=" * 70)
        logger.info("✓ MCPO wrapper started successfully")
        logger.info("=" * 70)
        logger.info(f"📡 OpenAPI endpoint: http://localhost:{args.mcpo_port}")
        logger.info(f"📚 API documentation: http://localhost:{args.mcpo_port}/docs")
        logger.info(f"🔍 Health check: http://localhost:{args.mcpo_port}/health")
        logger.info("=" * 70)
        logger.info("Press Ctrl+C to stop")

        # Wait for wrapper process
        if wrapper.process:
            wrapper.process.wait()

    except KeyboardInterrupt:
        logger.info("Shutdown initiated by user")
        if wrapper:
            wrapper.stop()
        sys.exit(0)
    except Exception as e:
        logger.error("Failed to start MCPO wrapper", error=str(e), error_type=type(e).__name__)
        sys.exit(1)
