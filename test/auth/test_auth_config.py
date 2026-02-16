#!/usr/bin/env python3
"""Tests for authentication configuration.

Tests the gofr_common.auth.config resolve_auth_config function
and the app.startup.auth_config thin wrapper.
"""

import os
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gofr_common.auth.config import resolve_auth_config
from app.startup.auth_config import resolve_jwt_secret_for_cli
from app.logger import Logger, session_logger


class TestResolveAuthConfig:
    """Tests for resolve_auth_config() function."""

    def test_returns_none_when_auth_disabled(self):
        """When require_auth=False, should return (None, False)."""
        logger: Logger = session_logger

        jwt_secret, require_auth = resolve_auth_config(
            env_prefix="GOFR_DOC",
            jwt_secret_arg=None,
            require_auth=False,
            logger=logger,
        )

        assert jwt_secret is None
        assert require_auth is False

    def test_prefers_cli_secret_over_environment(self):
        """CLI argument should take precedence over environment variable."""
        logger: Logger = session_logger
        cli_secret = "cli-provided-secret"
        env_secret = "env-provided-secret"

        # Set environment variable
        original_env = os.environ.get("GOFR_DOC_JWT_SECRET")
        os.environ["GOFR_DOC_JWT_SECRET"] = env_secret

        try:
            jwt_secret, _ = resolve_auth_config(
                env_prefix="GOFR_DOC",
                jwt_secret_arg=cli_secret,
                require_auth=True,
                logger=logger,
            )

            assert jwt_secret == cli_secret
        finally:
            if original_env:
                os.environ["GOFR_DOC_JWT_SECRET"] = original_env
            else:
                os.environ.pop("GOFR_DOC_JWT_SECRET", None)

    def test_uses_environment_when_cli_arg_none(self):
        """Should use environment variable when CLI arg is None."""
        logger: Logger = session_logger
        env_secret = "env-provided-secret"

        original_env = os.environ.get("GOFR_DOC_JWT_SECRET")
        os.environ["GOFR_DOC_JWT_SECRET"] = env_secret

        try:
            jwt_secret, _ = resolve_auth_config(
                env_prefix="GOFR_DOC",
                jwt_secret_arg=None,
                require_auth=True,
                logger=logger,
            )

            assert jwt_secret == env_secret
        finally:
            if original_env:
                os.environ["GOFR_DOC_JWT_SECRET"] = original_env
            else:
                os.environ.pop("GOFR_DOC_JWT_SECRET", None)

    def test_exits_when_secret_required_but_missing(self):
        """Should exit when auth required but no secret provided and auto disabled."""
        logger: Logger = session_logger

        original_env = os.environ.get("GOFR_DOC_JWT_SECRET")
        os.environ.pop("GOFR_DOC_JWT_SECRET", None)

        try:
            with pytest.raises(SystemExit) as exc_info:
                resolve_auth_config(
                    env_prefix="GOFR_DOC",
                    jwt_secret_arg=None,
                    require_auth=True,
                    allow_auto_secret=False,
                    exit_on_missing=True,
                    logger=logger,
                )

            assert exc_info.value.code == 1
        finally:
            if original_env:
                os.environ["GOFR_DOC_JWT_SECRET"] = original_env


class TestResolveJwtSecretForCli:
    """Tests for resolve_jwt_secret_for_cli() function."""

    def test_prefers_cli_secret_over_environment(self):
        """CLI argument should take precedence over environment variable."""
        logger: Logger = session_logger
        cli_secret = "cli-provided-secret"
        env_secret = "env-provided-secret"

        original_env = os.environ.get("GOFR_DOC_JWT_SECRET")
        os.environ["GOFR_DOC_JWT_SECRET"] = env_secret

        try:
            result = resolve_jwt_secret_for_cli(
                env_prefix="GOFR_DOC",
                cli_secret=cli_secret,
                logger=logger,
            )

            assert result == cli_secret
        finally:
            if original_env:
                os.environ["GOFR_DOC_JWT_SECRET"] = original_env
            else:
                os.environ.pop("GOFR_DOC_JWT_SECRET", None)

    def test_uses_environment_when_cli_none(self):
        """Should use environment variable when CLI arg is None."""
        logger: Logger = session_logger
        env_secret = "env-provided-secret"

        original_env = os.environ.get("GOFR_DOC_JWT_SECRET")
        os.environ["GOFR_DOC_JWT_SECRET"] = env_secret

        try:
            result = resolve_jwt_secret_for_cli(
                env_prefix="GOFR_DOC",
                cli_secret=None,
                logger=logger,
            )

            assert result == env_secret
        finally:
            if original_env:
                os.environ["GOFR_DOC_JWT_SECRET"] = original_env
            else:
                os.environ.pop("GOFR_DOC_JWT_SECRET", None)

    def test_exits_when_no_secret_provided(self):
        """Should call sys.exit(1) when no secret can be resolved."""
        logger: Logger = session_logger

        original_env = os.environ.get("GOFR_DOC_JWT_SECRET")
        os.environ.pop("GOFR_DOC_JWT_SECRET", None)

        try:
            with pytest.raises(SystemExit) as exc_info:
                resolve_jwt_secret_for_cli(
                    env_prefix="GOFR_DOC",
                    cli_secret=None,
                    logger=logger,
                )

            assert exc_info.value.code == 1
        finally:
            if original_env:
                os.environ["GOFR_DOC_JWT_SECRET"] = original_env


class TestIntegrationWithEntryPoints:
    """Integration tests verifying entry points use auth_config correctly."""

    def test_main_mcp_imports_auth_config(self):
        """Verify main_mcp.py imports resolve_auth_config from gofr_common."""
        with open("app/main_mcp.py") as f:
            content = f.read()

        assert "from gofr_common.auth.config import resolve_auth_config" in content
        assert "resolve_auth_config(" in content

    def test_main_web_imports_auth_config(self):
        """Verify main_web.py imports resolve_auth_config from gofr_common."""
        with open("app/main_web.py") as f:
            content = f.read()

        assert "from gofr_common.auth.config import resolve_auth_config" in content
        assert "resolve_auth_config(" in content

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
