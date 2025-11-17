"""Startup utilities for doco services."""

from .auth_config import resolve_auth_config, resolve_jwt_secret_for_cli

__all__ = ["resolve_auth_config", "resolve_jwt_secret_for_cli"]
