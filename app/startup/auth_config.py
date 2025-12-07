"""Authentication configuration utilities for GOFR-DOC server.

Re-exports resolve_auth_config from gofr_common.auth.config with
GOFR_DOC-specific defaults.
"""

from pathlib import Path
from typing import Optional, Tuple

from gofr_common.auth.config import (
    resolve_auth_config as _resolve_auth_config,
    resolve_jwt_secret_for_cli as _resolve_jwt_secret_for_cli,
)
from gofr_common.logger import Logger

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
    """
    # Use default token store path if not provided
    default_token_store = get_default_token_store_path()
    effective_token_store = token_store_arg or default_token_store

    # GOFR_DOC does NOT allow auto-generation - requires explicit secret
    jwt_secret, token_store_path, _ = _resolve_auth_config(
        env_prefix="GOFR_DOC",
        jwt_secret_arg=jwt_secret_arg,
        token_store_arg=effective_token_store,
        require_auth=require_auth,
        allow_auto_secret=False,  # GOFR_DOC requires explicit secret
        exit_on_missing=True,
        logger=logger,
    )

    # Convert Path to string for backward compatibility
    token_store_str = str(token_store_path) if token_store_path else None
    return jwt_secret, token_store_str


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
    return _resolve_jwt_secret_for_cli(
        env_prefix="GOFR_DOC",
        cli_secret=cli_secret,
        exit_on_missing=True,
        logger=logger,
    )
