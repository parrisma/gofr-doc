"""Pytest configuration and fixtures

Provides shared fixtures for all tests, including temporary data directories.
"""

import sys
from pathlib import Path

# Add project root to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import tempfile
import shutil
from app.config import Config
from app.storage import reset_storage, get_storage
from app.storage.file_storage import FileStorage
from app.auth import AuthService


@pytest.fixture(scope="function", autouse=True)
def test_data_dir(tmp_path):
    """
    Automatically provide a temporary data directory for each test

    This fixture:
    - Creates a unique temporary directory for each test
    - Configures app.config to use this directory
    - Cleans up after the test completes
    - Resets storage singleton to ensure fresh state
    - Purges all images from storage after test
    """
    # Set up test mode with temporary directory
    test_dir = tmp_path / "doco_test_data"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (test_dir / "storage").mkdir(exist_ok=True)
    (test_dir / "auth").mkdir(exist_ok=True)

    # Configure for testing
    Config.set_test_mode(test_dir)

    # Reset storage singleton to ensure tests get fresh storage with test directory
    reset_storage()

    yield test_dir

    # Cleanup: Purge all images from storage
    try:
        storage = get_storage()
        storage.purge(age_days=0)  # Delete all images
    except Exception:
        pass  # Ignore errors during cleanup

    Config.clear_test_mode()
    reset_storage()  # Reset storage after test


@pytest.fixture(scope="function")
def temp_storage_dir(tmp_path):
    """
    Provide a temporary storage directory for specific tests that need it

    Returns:
        Path object pointing to temporary storage directory
    """
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


@pytest.fixture(scope="function")
def temp_auth_dir(tmp_path):
    """
    Provide a temporary auth directory for specific tests that need it

    Returns:
        Path object pointing to temporary auth directory
    """
    auth_dir = tmp_path / "auth"
    auth_dir.mkdir(parents=True, exist_ok=True)
    return auth_dir


@pytest.fixture(scope="session")
def test_auth_service():
    """
    Create an AuthService instance for testing with a shared token store

    Uses the same secret as documented in TEST_AUTH.md for consistency.
    The MCP server must be started with:
      --jwt-secret "test-secret-key-for-auth-testing"
      --token-store "/tmp/doco_test_tokens.json"

    Returns:
        AuthService: Configured auth service for testing
    """
    test_secret = "test-secret-key-for-auth-testing"
    # Use a shared token store path that matches the MCP server launch config
    token_store_path = "/tmp/doco_test_tokens.json"

    auth_service = AuthService(secret_key=test_secret, token_store_path=token_store_path)
    return auth_service


@pytest.fixture(scope="function")
def test_jwt_token(test_auth_service):
    """
    Provide a valid JWT token for tests that require authentication.
    Token is created at test start and revoked at test end.

    Returns:
        str: A valid JWT token for testing
    """
    # Create token
    token = test_auth_service.create_token(group="test_group", expires_in_seconds=3600)

    yield token

    # Cleanup: revoke token after test
    try:
        test_auth_service.revoke_token(token)
    except Exception:
        pass  # Token may already be revoked or expired
