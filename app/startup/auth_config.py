"""Authentication configuration utilities for GOFR-DOC server.

Thin wrapper re-exporting from gofr_common.auth.config with
GOFR_DOC-specific defaults. Server entry points import directly
from gofr_common.auth.config; this module exists only for CLI tools
(e.g. token_manager) that use resolve_jwt_secret_for_cli.
"""

from gofr_common.auth.config import (
    resolve_auth_config,
    resolve_jwt_secret_for_cli,
)

__all__ = [
    "resolve_auth_config",
    "resolve_jwt_secret_for_cli",
]
