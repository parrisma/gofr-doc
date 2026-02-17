#!/usr/bin/env python3
"""Test JWT authentication and token management

Uses Vault-backed auth service from conftest fixtures.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import time
from datetime import datetime
from gofr_common.auth import AuthService, JwtSecretProvider
from gofr_common.auth.backends import VaultClient
from app.logger import Logger, session_logger


# Test configuration
TEST_GROUP = "secure"
TEST_EXPIRY_SECONDS = 90
TEST_JWT_SECRET = "test-secret-key-for-secure-testing-do-not-use-in-production"


def make_test_secret_provider(secret: str = TEST_JWT_SECRET) -> JwtSecretProvider:
    """Create a JwtSecretProvider backed by a mock VaultClient for testing."""
    from unittest.mock import MagicMock

    mock_vault = MagicMock(spec=VaultClient)
    mock_vault.read_secret.return_value = {"value": secret}
    return JwtSecretProvider(vault_client=mock_vault)


@pytest.fixture
def test_token(auth_service):
    """Create a test token for the 'secure' group"""
    auth_service._group_registry.create_group(TEST_GROUP, "Secure test group")
    token = auth_service.create_token(groups=[TEST_GROUP], expires_in_seconds=TEST_EXPIRY_SECONDS)
    return token


class TestAuthTokenCreation:
    """Test token creation and validation"""

    def test_create_token(self, auth_service):
        """Test token creation with correct parameters"""
        logger: Logger = session_logger
        logger.info("Testing token creation", group=TEST_GROUP, expiry_seconds=TEST_EXPIRY_SECONDS)

        auth_service._group_registry.create_group(TEST_GROUP, "Secure test group")
        token = auth_service.create_token(
            groups=[TEST_GROUP], expires_in_seconds=TEST_EXPIRY_SECONDS
        )

        # Verify token is created
        assert token is not None, "Token should not be None"
        assert isinstance(token, str), "Token should be a string"
        assert len(token) > 0, "Token should not be empty"

        logger.info("Token created successfully", token_length=len(token))

        # Verify token can be validated
        token_info = auth_service.verify_token(token)
        assert (
            TEST_GROUP in token_info.groups
        ), f"Group mismatch: expected {TEST_GROUP} in {token_info.groups}"

        # Verify expiry is correct (within 2 second tolerance)
        now = datetime.utcnow()
        expiry_delta = (token_info.expires_at - now).total_seconds()
        assert (
            abs(expiry_delta - TEST_EXPIRY_SECONDS) < 2
        ), f"Expiry mismatch: expected ~{TEST_EXPIRY_SECONDS}s, got {expiry_delta}s"

        logger.info("Token validation passed", groups=token_info.groups, expires_in=expiry_delta)

    def test_create_multiple_tokens_different_groups(self, auth_service):
        """Test creating tokens for different groups"""
        logger: Logger = session_logger
        logger.info("Testing multiple tokens for different groups")

        groups = ["group1", "group2", "group3"]
        tokens = {}

        for group in groups:
            auth_service._group_registry.create_group(group, f"Test group {group}")
            token = auth_service.create_token(groups=[group], expires_in_seconds=60)
            tokens[group] = token

            # Verify each token
            token_info = auth_service.verify_token(token)
            assert group in token_info.groups, f"Group mismatch for {group}"

        logger.info("Multiple tokens created and validated", groups=len(tokens))

        # List all tokens
        listed = auth_service.list_tokens()
        assert len(listed) == 3, f"Expected 3 tokens, found {len(listed)}"

    def test_verify_token_with_wrong_secret(self, auth_service):
        """Test that tokens created with different secret cannot be verified"""
        logger: Logger = session_logger
        logger.info("Testing token verification with wrong secret")

        auth_service._group_registry.create_group(TEST_GROUP, "Secure test group")
        token = auth_service.create_token(groups=[TEST_GROUP], expires_in_seconds=60)

        # Create second auth service with wrong secret, sharing same stores
        wrong_service = AuthService(
            token_store=auth_service._token_store,
            group_registry=auth_service._group_registry,
            secret_provider=make_test_secret_provider("wrong-secret"),
            env_prefix="GOFR_DOC",
        )

        with pytest.raises(Exception):  # Should raise authentication error
            wrong_service.verify_token(token)

        logger.info("Token correctly rejected with wrong secret")

    def test_token_storage_persistence(self, auth_service):
        """Test that tokens persist across AuthService instances via Vault"""
        logger: Logger = session_logger
        logger.info("Testing token persistence via Vault")

        auth_service._group_registry.create_group(TEST_GROUP, "Secure test group")
        token = auth_service.create_token(groups=[TEST_GROUP], expires_in_seconds=60)
        logger.info("Token created with service1", token=token[:20])

        # Create second service with same Vault stores
        service2 = AuthService(
            token_store=auth_service._token_store,
            group_registry=auth_service._group_registry,
            secret_provider=make_test_secret_provider(TEST_JWT_SECRET),
            env_prefix="GOFR_DOC",
            audience="gofr-api",
        )

        # Verify token exists in second service
        token_info = service2.verify_token(token)
        assert TEST_GROUP in token_info.groups, "Token not persisted in Vault"

        logger.info("Token persisted across service instances")

    def test_revoke_token(self, auth_service, test_token):
        """Test token revocation"""
        logger: Logger = session_logger
        logger.info("Testing token revocation")

        # Verify token works before revocation
        token_info = auth_service.verify_token(test_token)
        assert token_info is not None, "Token should be valid before revocation"

        # Revoke the token
        auth_service.revoke_token(test_token)
        logger.info("Token revoked")

        # Verify token no longer works
        with pytest.raises(Exception):  # Should raise authentication error
            auth_service.verify_token(test_token)

        logger.info("Token correctly rejected after revocation")

    def test_list_tokens(self, auth_service):
        """Test listing all tokens"""
        logger: Logger = session_logger
        logger.info("Testing list_tokens")

        # Create several tokens with different groups
        groups = ["test1", "test2", "test3"]
        for group in groups:
            auth_service._group_registry.create_group(group, f"Test group {group}")
            auth_service.create_token(groups=[group], expires_in_seconds=60)

        # List tokens
        tokens = auth_service.list_tokens()
        assert len(tokens) == 3, f"Expected 3 tokens, found {len(tokens)}"

        # Verify each token record has expected fields
        for record in tokens:
            assert hasattr(record, "groups"), "Missing groups in token record"
            assert hasattr(record, "created_at"), "Missing created_at in token record"
            assert hasattr(record, "expires_at"), "Missing expires_at in token record"
            assert any(g in groups for g in record.groups), f"Unexpected groups: {record.groups}"

        logger.info("Listed tokens verified", count=len(tokens))

    def test_token_expiry_validation(self, auth_service):
        """Test that expired tokens are rejected"""
        logger: Logger = session_logger
        logger.info("Testing token expiry validation")

        # Create token with very short expiry
        auth_service._group_registry.create_group("expiry_test", "Expiry test group")
        token = auth_service.create_token(groups=["expiry_test"], expires_in_seconds=1)
        logger.info("Short-lived token created, waiting for expiry...")

        # Verify token works immediately
        token_info = auth_service.verify_token(token)
        assert token_info is not None, "Token should be valid immediately"

        # Wait for expiry
        time.sleep(2)

        # Verify token is expired
        with pytest.raises(Exception):  # Should raise expiry error
            auth_service.verify_token(token)

        logger.info("Expired token correctly rejected")

    def test_group_segregation(self, auth_service):
        """Test that groups are properly segregated"""
        logger: Logger = session_logger
        logger.info("Testing group segregation")

        # Create tokens for different groups
        auth_service._group_registry.create_group("group1", "Group 1")
        auth_service._group_registry.create_group("group2", "Group 2")
        token1 = auth_service.create_token(groups=["group1"], expires_in_seconds=60)
        token2 = auth_service.create_token(groups=["group2"], expires_in_seconds=60)

        # Verify tokens belong to correct groups
        info1 = auth_service.verify_token(token1)
        info2 = auth_service.verify_token(token2)

        assert "group1" in info1.groups, "Token1 should belong to group1"
        assert "group2" in info2.groups, "Token2 should belong to group2"
        assert info1.groups != info2.groups, "Tokens should have different groups"

        logger.info("Groups properly segregated", group1=info1.groups, group2=info2.groups)

    def test_create_token_with_default_expiry(self, auth_service):
        """Test token creation with default expiry"""
        logger: Logger = session_logger
        logger.info("Testing token with default expiry")

        # Create token without specifying expiry (should use default: 30 days)
        auth_service._group_registry.create_group("default_test", "Default expiry test")
        token = auth_service.create_token(groups=["default_test"])

        token_info = auth_service.verify_token(token)

        # Default is 30 days = 2592000 seconds
        now = datetime.utcnow()
        expiry_delta = (token_info.expires_at - now).total_seconds()

        # Should be approximately 30 days (within 2 seconds)
        expected = 2592000
        assert (
            abs(expiry_delta - expected) < 2
        ), f"Default expiry should be ~30 days ({expected}s), got {expiry_delta}s"

        logger.info("Default token expiry correct", expiry_seconds=expiry_delta)

    def test_invalid_token_format(self, auth_service):
        """Test that invalid token format is rejected"""
        logger: Logger = session_logger
        logger.info("Testing invalid token format")

        invalid_tokens = [
            "not-a-token",
            "not.a.jwt.token.either",
            "",
            "x" * 100,
        ]

        for invalid_token in invalid_tokens:
            with pytest.raises(Exception):  # Should raise validation error
                auth_service.verify_token(invalid_token)

        logger.info("Invalid tokens correctly rejected")


if __name__ == "__main__":
    # Run all tests
    import pytest

    sys.exit(pytest.main([__file__, "-v", "-s"]))
