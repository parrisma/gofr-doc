"""Authentication configuration utilities for GOFR-DOC server.

Previously re-exported resolve_auth_config and resolve_jwt_secret_for_cli
from gofr_common.auth.config. Those functions have been removed -- JWT
secrets are now always resolved via JwtSecretProvider backed by Vault.
"""
