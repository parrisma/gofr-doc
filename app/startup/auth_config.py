"""Shared authentication configuration for server and CLI entry points.

Provides consistent resolution and validation of JWT secrets and token store paths.
"""

import os
import sys
from typing import Optional, Tuple
from app.logger import Logger
from app.config import get_default_token_store_path


def resolve_auth_config(
    jwt_secret_arg: Optional[str],
    token_store_arg: Optional[str],
    require_auth: bool,
    logger: Logger,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve JWT secret and token store path from arguments and environment.

    Args:
        jwt_secret_arg: JWT secret from CLI argument (or None)
        token_store_arg: Token store path from CLI argument (or None)
        require_auth: Whether authentication is required
        logger: Logger instance for diagnostics

    Returns:
        Tuple of (jwt_secret, token_store_path) or (None, None) if auth disabled

    Raises:
        SystemExit: If auth is required but secret is missing
    """
    if not require_auth:
        logger.info("Authentication disabled via --no-auth flag")
        return None, None

    # Resolve JWT secret from CLI arg or environment
    jwt_secret = jwt_secret_arg or os.environ.get("GOFR_DOC_JWT_SECRET")

    if not jwt_secret:
        logger.error(
            "FATAL: Authentication enabled but no JWT secret provided",
            suggestion="Set GOFR_DOC_JWT_SECRET environment variable, use --jwt-secret flag, or use --no-auth to disable authentication",
        )
        sys.exit(1)

    # Resolve token store path
    token_store_path = token_store_arg
    if not token_store_path:
        # Try environment variable
        token_store_path = os.environ.get("GOFR_DOC_TOKEN_STORE")
    if not token_store_path:
        # Fall back to configured default
        token_store_path = get_default_token_store_path()

    logger.info(
        "Authentication configuration resolved",
        jwt_secret_source="CLI" if jwt_secret_arg else "environment",
        token_store=token_store_path,
    )

    return jwt_secret, token_store_path


def resolve_jwt_secret_for_cli(
    cli_secret: Optional[str],
    logger: Logger,
) -> str:
    """
    Resolve JWT secret for CLI scripts (token_manager, etc).

    Args:
        cli_secret: Secret from --secret CLI argument
        logger: Logger instance

    Returns:
        JWT secret string

    Raises:
        SystemExit: If no secret can be resolved
    """
    secret = cli_secret or os.environ.get("GOFR_DOC_JWT_SECRET")

    if not secret:
        logger.error(
            "FATAL: No JWT secret provided",
            suggestion="Set GOFR_DOC_JWT_SECRET environment variable or use --secret flag",
        )
        sys.exit(1)

    logger.info(
        "JWT secret resolved",
        source="CLI" if cli_secret else "environment",
    )

    return secret
