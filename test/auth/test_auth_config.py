#!/usr/bin/env python3
"""Tests for centralized authentication configuration (Phase 1).

Tests the auth_config module that provides consistent JWT secret and
token store resolution for all server and CLI entry points.
"""

import os
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.startup.auth_config import resolve_auth_config, resolve_jwt_secret_for_cli
from app.logger import Logger, session_logger


class TestResolveAuthConfig:
    """Tests for resolve_auth_config() function."""

    def test_returns_none_when_auth_disabled(self):
        """When require_auth=False, should return (None, None)."""
        logger: Logger = session_logger

        result = resolve_auth_config(
            jwt_secret_arg=None,
            token_store_arg=None,
            require_auth=False,
            logger=logger,
        )

        assert result == (None, None)

    def test_prefers_cli_secret_over_environment(self):
        """CLI argument should take precedence over environment variable."""
        logger: Logger = session_logger
        cli_secret = "cli-provided-secret"
        env_secret = "env-provided-secret"

        # Set environment variable
        original_env = os.environ.get("DOCO_JWT_SECRET")
        os.environ["DOCO_JWT_SECRET"] = env_secret

        try:
            jwt_secret, _ = resolve_auth_config(
                jwt_secret_arg=cli_secret,
                token_store_arg=None,
                require_auth=True,
                logger=logger,
            )

            assert jwt_secret == cli_secret
        finally:
            # Restore original environment
            if original_env:
                os.environ["DOCO_JWT_SECRET"] = original_env
            else:
                os.environ.pop("DOCO_JWT_SECRET", None)

    def test_uses_environment_when_cli_arg_none(self):
        """Should use environment variable when CLI arg is None."""
        logger: Logger = session_logger
        env_secret = "env-provided-secret"

        # Set environment variable
        original_env = os.environ.get("DOCO_JWT_SECRET")
        os.environ["DOCO_JWT_SECRET"] = env_secret

        try:
            jwt_secret, _ = resolve_auth_config(
                jwt_secret_arg=None,
                token_store_arg=None,
                require_auth=True,
                logger=logger,
            )

            assert jwt_secret == env_secret
        finally:
            # Restore original environment
            if original_env:
                os.environ["DOCO_JWT_SECRET"] = original_env
            else:
                os.environ.pop("DOCO_JWT_SECRET", None)

    def test_exits_when_secret_required_but_missing(self):
        """Should call sys.exit(1) when auth required but no secret provided."""
        logger: Logger = session_logger

        # Clear environment variable
        original_env = os.environ.get("DOCO_JWT_SECRET")
        os.environ.pop("DOCO_JWT_SECRET", None)

        try:
            with pytest.raises(SystemExit) as exc_info:
                resolve_auth_config(
                    jwt_secret_arg=None,
                    token_store_arg=None,
                    require_auth=True,
                    logger=logger,
                )

            assert exc_info.value.code == 1
        finally:
            # Restore original environment
            if original_env:
                os.environ["DOCO_JWT_SECRET"] = original_env

    def test_prefers_cli_token_store_over_environment(self):
        """CLI token store argument should take precedence."""
        logger: Logger = session_logger
        cli_store = "/cli/token/store.json"
        env_store = "/env/token/store.json"

        # Set environment variables
        original_secret = os.environ.get("DOCO_JWT_SECRET")
        original_store = os.environ.get("DOCO_TOKEN_STORE")
        os.environ["DOCO_JWT_SECRET"] = "test-secret"
        os.environ["DOCO_TOKEN_STORE"] = env_store

        try:
            _, token_store = resolve_auth_config(
                jwt_secret_arg="test-secret",
                token_store_arg=cli_store,
                require_auth=True,
                logger=logger,
            )

            assert token_store == cli_store
        finally:
            # Restore original environment
            if original_secret:
                os.environ["DOCO_JWT_SECRET"] = original_secret
            else:
                os.environ.pop("DOCO_JWT_SECRET", None)

            if original_store:
                os.environ["DOCO_TOKEN_STORE"] = original_store
            else:
                os.environ.pop("DOCO_TOKEN_STORE", None)

    def test_uses_environment_token_store_when_cli_none(self):
        """Should use environment variable for token store when CLI arg is None."""
        logger: Logger = session_logger
        env_store = "/env/token/store.json"

        # Set environment variables
        original_secret = os.environ.get("DOCO_JWT_SECRET")
        original_store = os.environ.get("DOCO_TOKEN_STORE")
        os.environ["DOCO_JWT_SECRET"] = "test-secret"
        os.environ["DOCO_TOKEN_STORE"] = env_store

        try:
            _, token_store = resolve_auth_config(
                jwt_secret_arg="test-secret",
                token_store_arg=None,
                require_auth=True,
                logger=logger,
            )

            assert token_store == env_store
        finally:
            # Restore original environment
            if original_secret:
                os.environ["DOCO_JWT_SECRET"] = original_secret
            else:
                os.environ.pop("DOCO_JWT_SECRET", None)

            if original_store:
                os.environ["DOCO_TOKEN_STORE"] = original_store
            else:
                os.environ.pop("DOCO_TOKEN_STORE", None)

    def test_uses_default_token_store_when_not_specified(self):
        """Should use default token store from config when neither CLI nor env specified."""
        logger: Logger = session_logger

        # Set environment variables
        original_secret = os.environ.get("DOCO_JWT_SECRET")
        original_store = os.environ.get("DOCO_TOKEN_STORE")
        os.environ["DOCO_JWT_SECRET"] = "test-secret"
        os.environ.pop("DOCO_TOKEN_STORE", None)  # Ensure env var not set

        try:
            _, token_store = resolve_auth_config(
                jwt_secret_arg="test-secret",
                token_store_arg=None,
                require_auth=True,
                logger=logger,
            )

            # Should get default from config (not None)
            assert token_store is not None
            assert isinstance(token_store, str)
            assert "token" in token_store.lower() or "auth" in token_store.lower()
        finally:
            # Restore original environment
            if original_secret:
                os.environ["DOCO_JWT_SECRET"] = original_secret
            else:
                os.environ.pop("DOCO_JWT_SECRET", None)

            if original_store:
                os.environ["DOCO_TOKEN_STORE"] = original_store


class TestResolveJwtSecretForCli:
    """Tests for resolve_jwt_secret_for_cli() function."""

    def test_prefers_cli_secret_over_environment(self):
        """CLI argument should take precedence over environment variable."""
        logger: Logger = session_logger
        cli_secret = "cli-provided-secret"
        env_secret = "env-provided-secret"

        # Set environment variable
        original_env = os.environ.get("DOCO_JWT_SECRET")
        os.environ["DOCO_JWT_SECRET"] = env_secret

        try:
            result = resolve_jwt_secret_for_cli(
                cli_secret=cli_secret,
                logger=logger,
            )

            assert result == cli_secret
        finally:
            # Restore original environment
            if original_env:
                os.environ["DOCO_JWT_SECRET"] = original_env
            else:
                os.environ.pop("DOCO_JWT_SECRET", None)

    def test_uses_environment_when_cli_none(self):
        """Should use environment variable when CLI arg is None."""
        logger: Logger = session_logger
        env_secret = "env-provided-secret"

        # Set environment variable
        original_env = os.environ.get("DOCO_JWT_SECRET")
        os.environ["DOCO_JWT_SECRET"] = env_secret

        try:
            result = resolve_jwt_secret_for_cli(
                cli_secret=None,
                logger=logger,
            )

            assert result == env_secret
        finally:
            # Restore original environment
            if original_env:
                os.environ["DOCO_JWT_SECRET"] = original_env
            else:
                os.environ.pop("DOCO_JWT_SECRET", None)

    def test_exits_when_no_secret_provided(self):
        """Should call sys.exit(1) when no secret can be resolved."""
        logger: Logger = session_logger

        # Clear environment variable
        original_env = os.environ.get("DOCO_JWT_SECRET")
        os.environ.pop("DOCO_JWT_SECRET", None)

        try:
            with pytest.raises(SystemExit) as exc_info:
                resolve_jwt_secret_for_cli(
                    cli_secret=None,
                    logger=logger,
                )

            assert exc_info.value.code == 1
        finally:
            # Restore original environment
            if original_env:
                os.environ["DOCO_JWT_SECRET"] = original_env


class TestIntegrationWithEntryPoints:
    """Integration tests verifying entry points use auth_config correctly."""

    def test_main_mcp_imports_auth_config(self):
        """Verify main_mcp.py imports resolve_auth_config."""
        with open("app/main_mcp.py") as f:
            content = f.read()

        assert "from app.startup.auth_config import resolve_auth_config" in content
        assert "resolve_auth_config(" in content

    def test_main_web_imports_auth_config(self):
        """Verify main_web.py imports resolve_auth_config."""
        with open("app/main_web.py") as f:
            content = f.read()

        assert "from app.startup.auth_config import resolve_auth_config" in content
        assert "resolve_auth_config(" in content

    def test_token_manager_imports_auth_config(self):
        """Verify token_manager.py imports resolve_jwt_secret_for_cli."""
        with open("app/management/token_manager.py") as f:
            content = f.read()

        assert "from app.startup.auth_config import resolve_jwt_secret_for_cli" in content
        assert "resolve_jwt_secret_for_cli(" in content

    def test_no_hardcoded_test_secrets_in_production_code(self):
        """Verify no hardcoded test secrets remain in production code."""
        # Check main entry points don't have hardcoded test secrets
        files_to_check = [
            "app/main_mcp.py",
            "app/main_web.py",
            "app/web_server/web_server.py",
            "app/management/token_manager.py",
        ]

        # This is the old test secret that should NOT appear in production code
        forbidden_secret = "test-secret-key-for-auth-testing"

        for filepath in files_to_check:
            with open(filepath) as f:
                content = f.read()

            assert forbidden_secret not in content, f"Found hardcoded test secret in {filepath}"

    def test_web_server_uses_injected_auth_service(self):
        """Verify web_server.py uses injected AuthService instead of manual JWT decoding."""
        with open("app/web_server/web_server.py") as f:
            content = f.read()

        # Should accept auth_service parameter
        assert "auth_service" in content

        # Should use auth_service.verify_token() for token verification
        assert "self.auth_service.verify_token" in content

        # Should NOT do manual JWT decoding anymore
        assert "jwt.decode" not in content

        # Should NOT check environment variable directly (that's done in main_web.py now)
        assert 'os.environ.get("DOCO_JWT_SECRET")' not in content
