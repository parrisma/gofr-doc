"""Authentication configuration utilities for GOFR-DOC server.

Re-exports resolve_auth_config from gofr_common.auth.config with
GOFR_DOC-specific defaults.
"""

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
    # Get default token store path for fallback
    default_token_store = get_default_token_store_path()

    # GOFR_DOC does NOT allow auto-generation - requires explicit secret
    # Pass token_store_arg directly (may be None) - let gofr_common check env vars
    jwt_secret, token_store_path, _ = _resolve_auth_config(
        env_prefix="GOFR_DOC",
        jwt_secret_arg=jwt_secret_arg,
        token_store_arg=token_store_arg,
        require_auth=require_auth,
        allow_auto_secret=False,  # GOFR_DOC requires explicit secret
        exit_on_missing=True,
        logger=logger,
    )

    # If gofr_common returned the default "data/auth/tokens.json", use our default
    if token_store_path and str(token_store_path) == "data/auth/tokens.json":
        token_store_path_str = default_token_store
    else:
        token_store_path_str = str(token_store_path) if token_store_path else None
    
    return jwt_secret, token_store_path_str


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
