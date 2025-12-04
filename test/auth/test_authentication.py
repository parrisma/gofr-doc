#!/usr/bin/env python3
"""Test JWT authentication and token management"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import tempfile
from datetime import datetime
from app.auth import AuthService
from app.logger import Logger, session_logger


# Test configuration
TEST_GROUP = "secure"
TEST_EXPIRY_SECONDS = 90

# Note: auth_service fixture overridden below for auth tests requiring isolation


@pytest.fixture
def auth_service():
    """
    Create an isolated AuthService for auth unit tests.

    Auth tests need isolated token stores to verify token counts, listing, etc.
    without interference from other tests using the shared store.
    """
    with tempfile.TemporaryDirectory(prefix="gofr_doc_auth_test_") as temp_dir:
        token_store = f"{temp_dir}/tokens.json"
        service = AuthService(
            secret_key="test-secret-key-for-secure-testing-do-not-use-in-production",
            token_store_path=token_store,
        )
        yield service


@pytest.fixture
def test_token(auth_service):
    """Create a test token for the 'secure' group"""
    token = auth_service.create_token(group=TEST_GROUP, expires_in_seconds=TEST_EXPIRY_SECONDS)
    return token


class TestAuthTokenCreation:
    """Test token creation and validation"""

    def test_create_token(self, auth_service):
        """Test token creation with correct parameters"""
        logger: Logger = session_logger
        logger.info("Testing token creation", group=TEST_GROUP, expiry_seconds=TEST_EXPIRY_SECONDS)

        token = auth_service.create_token(group=TEST_GROUP, expires_in_seconds=TEST_EXPIRY_SECONDS)

        # Verify token is created
        assert token is not None, "Token should not be None"
        assert isinstance(token, str), "Token should be a string"
        assert len(token) > 0, "Token should not be empty"

        logger.info("Token created successfully", token_length=len(token))

        # Verify token can be validated
        token_info = auth_service.verify_token(token)
        assert (
            token_info.group == TEST_GROUP
        ), f"Group mismatch: expected {TEST_GROUP}, got {token_info.group}"

        # Verify expiry is correct (within 1 second tolerance)
        now = datetime.utcnow()
        expiry_delta = (token_info.expires_at - now).total_seconds()
        assert (
            abs(expiry_delta - TEST_EXPIRY_SECONDS) < 2
        ), f"Expiry mismatch: expected ~{TEST_EXPIRY_SECONDS}s, got {expiry_delta}s"

        logger.info("Token validation passed", group=token_info.group, expires_in=expiry_delta)

    def test_create_multiple_tokens_different_groups(self, auth_service):
        """Test creating tokens for different groups"""
        logger: Logger = session_logger
        logger.info("Testing multiple tokens for different groups")

        groups = ["group1", "group2", "group3"]
        tokens = {}

        for group in groups:
            token = auth_service.create_token(group=group, expires_in_seconds=60)
            tokens[group] = token

            # Verify each token
            token_info = auth_service.verify_token(token)
            assert token_info.group == group, f"Group mismatch for {group}"

        logger.info("Multiple tokens created and validated", groups=len(tokens))

        # List all tokens
        listed = auth_service.list_tokens()
        assert len(listed) == 3, f"Expected 3 tokens, found {len(listed)}"

    def test_verify_token_with_wrong_secret(self, auth_service):
        """Test that tokens created with different secret cannot be verified"""
        logger: Logger = session_logger
        logger.info("Testing token verification with wrong secret")

        # Create token with correct secret
        token = auth_service.create_token(group=TEST_GROUP, expires_in_seconds=60)

        # Try to verify with wrong secret
        wrong_service = AuthService(secret_key="wrong-secret", token_store_path="/tmp/wrong.json")

        with pytest.raises(Exception):  # Should raise authentication error
            wrong_service.verify_token(token)

        logger.info("Token correctly rejected with wrong secret")

    def test_token_storage_persistence(self):
        """Test that tokens persist across AuthService instances"""
        logger: Logger = session_logger
        logger.info("Testing token persistence")

        TEST_JWT_SECRET = "test-secret-key-for-secure-testing-do-not-use-in-production"

        with tempfile.TemporaryDirectory(prefix="gofr_doc_persist_test_") as temp_dir:
            token_store = f"{temp_dir}/tokens.json"

            # Create first service and token
            service1 = AuthService(secret_key=TEST_JWT_SECRET, token_store_path=token_store)
            token = service1.create_token(group=TEST_GROUP, expires_in_seconds=60)
            logger.info("Token created with service1", token=token[:20])

            # Create second service with same token store
            service2 = AuthService(secret_key=TEST_JWT_SECRET, token_store_path=token_store)

            # Verify token exists in second service
            token_info = service2.verify_token(token)
            assert token_info.group == TEST_GROUP, "Token not persisted"

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

        # Create several tokens
        groups = ["test1", "test2", "test3"]
        for group in groups:
            auth_service.create_token(group=group, expires_in_seconds=60)

        # List tokens
        tokens = auth_service.list_tokens()
        assert len(tokens) == 3, f"Expected 3 tokens, found {len(tokens)}"

        # Verify each token has expected fields
        for token, info in tokens.items():
            assert "group" in info, "Missing group in token info"
            assert "issued_at" in info, "Missing issued_at in token info"
            assert "expires_at" in info, "Missing expires_at in token info"
            assert info["group"] in groups, f"Unexpected group: {info['group']}"

        logger.info("Listed tokens verified", count=len(tokens))

    def test_token_expiry_validation(self, auth_service):
        """Test that expired tokens are rejected"""
        logger: Logger = session_logger
        logger.info("Testing token expiry validation")

        # Create token with very short expiry
        import time

        token = auth_service.create_token(group="test", expires_in_seconds=1)
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
        token1 = auth_service.create_token(group="group1", expires_in_seconds=60)
        token2 = auth_service.create_token(group="group2", expires_in_seconds=60)

        # Verify tokens belong to correct groups
        info1 = auth_service.verify_token(token1)
        info2 = auth_service.verify_token(token2)

        assert info1.group == "group1", "Token1 should belong to group1"
        assert info2.group == "group2", "Token2 should belong to group2"
        assert info1.group != info2.group, "Tokens should have different groups"

        logger.info("Groups properly segregated", group1=info1.group, group2=info2.group)

    def test_create_token_with_default_expiry(self, auth_service):
        """Test token creation with default expiry"""
        logger: Logger = session_logger
        logger.info("Testing token with default expiry")

        # Create token without specifying expiry (should use default: 30 days)
        token = auth_service.create_token(group="test")

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
