#!/usr/bin/env python3
"""Tests for authentication configuration.

Tests that entry points use the JwtSecretProvider/create_vault_client_from_env
pattern and that the old config functions have been removed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest


class TestOldConfigRemoved:
    """Verify the old resolve_auth_config / resolve_jwt_secret_for_cli are gone."""

    def test_resolve_auth_config_removed(self):
        """resolve_auth_config should no longer be importable."""
        with pytest.raises(ImportError):
            from gofr_common.auth.config import resolve_auth_config  # noqa: F401

    def test_resolve_jwt_secret_for_cli_removed(self):
        """resolve_jwt_secret_for_cli should no longer be importable."""
        with pytest.raises(ImportError):
            from gofr_common.auth.config import resolve_jwt_secret_for_cli  # noqa: F401


class TestJwtSecretProviderImportable:
    """Verify JwtSecretProvider is importable from gofr_common.auth."""

    def test_import_from_auth(self):
        from gofr_common.auth import JwtSecretProvider

        assert JwtSecretProvider is not None

    def test_import_from_module(self):
        from gofr_common.auth.jwt_secret_provider import JwtSecretProvider

        assert JwtSecretProvider is not None


class TestVaultClientFactoryImportable:
    """Verify create_vault_client_from_env is importable."""

    def test_import_from_auth(self):
        from gofr_common.auth import create_vault_client_from_env

        assert callable(create_vault_client_from_env)

    def test_import_from_backends(self):
        from gofr_common.auth.backends import create_vault_client_from_env

        assert callable(create_vault_client_from_env)


class TestIntegrationWithEntryPoints:
    """Integration tests verifying entry points use the provider pattern."""

    def test_main_mcp_uses_provider_pattern(self):
        """Verify main_mcp.py uses create_vault_client_from_env + JwtSecretProvider."""
        with open("app/main_mcp.py") as f:
            content = f.read()

        assert "create_vault_client_from_env" in content
        assert "JwtSecretProvider" in content
        assert "secret_provider" in content
        # Old patterns should be gone
        assert "resolve_auth_config" not in content
        assert "--jwt-secret" not in content

    def test_main_web_uses_provider_pattern(self):
        """Verify main_web.py uses create_vault_client_from_env + JwtSecretProvider."""
        with open("app/main_web.py") as f:
            content = f.read()

        assert "create_vault_client_from_env" in content
        assert "JwtSecretProvider" in content
        assert "secret_provider" in content
        # Old patterns should be gone
        assert "resolve_auth_config" not in content
        assert "--jwt-secret" not in content

    def test_no_hardcoded_test_secrets_in_production_code(self):
        """Verify no hardcoded test secrets remain in production code."""
        files_to_check = [
            "app/main_mcp.py",
            "app/main_web.py",
            "app/web_server/web_server.py",
        ]

        forbidden_secret = "test-secret-key-for-auth-testing"

        for filepath in files_to_check:
            with open(filepath) as f:
                content = f.read()

            assert forbidden_secret not in content, f"Found hardcoded test secret in {filepath}"

    def test_no_token_store_path_in_server_entry_points(self):
        """Verify server entry points no longer reference token_store_path."""
        for filepath in ["app/main_mcp.py", "app/main_web.py"]:
            with open(filepath) as f:
                content = f.read()

            assert (
                "token_store_path" not in content
            ), f"Found token_store_path reference in {filepath}"
            assert "--token-store" not in content, f"Found --token-store argument in {filepath}"

    def test_server_entry_points_use_vault_stores(self):
        """Verify server entry points use create_stores_from_env."""
        for filepath in ["app/main_mcp.py", "app/main_web.py"]:
            with open(filepath) as f:
                content = f.read()

            assert (
                "create_stores_from_env" in content
            ), f"Missing create_stores_from_env in {filepath}"
            assert "GroupRegistry" in content, f"Missing GroupRegistry in {filepath}"

    def test_no_gofr_jwt_secret_env_in_production_code(self):
        """Verify production code does not reference GOFR_JWT_SECRET env var."""
        files_to_check = [
            "app/main_mcp.py",
            "app/main_web.py",
        ]

        for filepath in files_to_check:
            with open(filepath) as f:
                content = f.read()

            assert (
                "GOFR_JWT_SECRET" not in content
            ), f"Found GOFR_JWT_SECRET reference in {filepath}"
