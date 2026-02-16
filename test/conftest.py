"""Pytest configuration and fixtures

Provides shared fixtures for all tests, including temporary data directories,
auth service setup, and test server token management.

Auth pattern: ALL fixtures use Vault-backed stores (no in-memory or file stores).
Each test gets a unique Vault path prefix for isolation.
Matches gofr-dig's conftest.py pattern.
"""

import os
import sys
from pathlib import Path

import pytest

from gofr_common.auth.groups import DuplicateGroupError

# Add project root to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from uuid import uuid4

from gofr_common.auth import AuthService, GroupRegistry
from gofr_common.auth.backends import VaultClient, VaultConfig, VaultGroupStore, VaultTokenStore
from gofr_common.auth.jwt_secret_provider import JwtSecretProvider
from app.config import Config
from app.storage import get_storage, reset_storage


# ============================================================================
# CONTENT BOOTSTRAP — symlink app/content/ into data/ for local test runs
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_content():
    """Ensure data/{templates,styles,fragments} exist by symlinking from app/content/.

    In prod/test Docker images the Dockerfile COPYs real files into data/.
    In the dev container the entrypoint creates symlinks.
    This fixture covers the case where tests run directly (e.g. pytest from CLI)
    without the entrypoint having run first.

    Also symlinks test/data/{templates,styles,fragments} so that render
    tests that use their own test_data_dir fixture find content too.
    """
    project_root = Path(__file__).parent.parent
    content_dir = project_root / "app" / "content"

    # Locations that need content symlinks
    targets = [
        project_root / "data",
        project_root / "test" / "data",
    ]

    for data_dir in targets:
        data_dir.mkdir(parents=True, exist_ok=True)
        for subdir in ("templates", "styles", "fragments"):
            target = data_dir / subdir
            source = content_dir / subdir
            if not source.is_dir():
                continue
            if target.is_symlink() or target.exists():
                # Already set up (symlink or real dir with content)
                continue
            target.symlink_to(source)


# ============================================================================
# AUTH AND TOKEN CONFIGURATION
# ============================================================================

# Shared JWT secret for all test servers and token generation
# Must match the secret used when launching test MCP/web servers
TEST_JWT_SECRET = "test-secret-key-for-secure-testing-do-not-use-in-production"

TEST_GROUP = "test_group"


def make_test_secret_provider(secret: str = TEST_JWT_SECRET) -> JwtSecretProvider:
    """Create a JwtSecretProvider backed by a mock VaultClient for testing.

    The mock always returns the given secret from Vault, providing the
    same interface as production but without a real Vault dependency.
    """
    from unittest.mock import MagicMock

    mock_vault = MagicMock(spec=VaultClient)
    mock_vault.read_secret.return_value = {"value": secret}
    return JwtSecretProvider(vault_client=mock_vault)


def _create_test_auth_service(vault_client: VaultClient, path_prefix: str) -> AuthService:
    """Create an AuthService backed by Vault for testing.

    Uses a unique path prefix per test instance to isolate data.
    Automatically bootstraps reserved groups (public, admin) and creates
    the test_group used across the test suite.
    """
    token_store = VaultTokenStore(vault_client, path_prefix=path_prefix)
    group_store = VaultGroupStore(vault_client, path_prefix=path_prefix)
    group_registry = GroupRegistry(store=group_store)  # auto-bootstraps public, admin
    try:
        group_registry.create_group(TEST_GROUP, "Test group for test suite")
    except DuplicateGroupError:
        pass

    return AuthService(
        token_store=token_store,
        group_registry=group_registry,
        secret_provider=make_test_secret_provider(),
        env_prefix="GOFR_DOC",
    )


def _build_vault_client() -> VaultClient:
    """Create a VaultClient for tests using GOFR_DOC_VAULT_* env vars."""
    vault_url = os.environ.get("GOFR_DOC_VAULT_URL")
    vault_token = os.environ.get("GOFR_DOC_VAULT_TOKEN")

    if not vault_url or not vault_token:
        raise RuntimeError(
            "Vault test configuration missing. Set GOFR_DOC_VAULT_URL and "
            "GOFR_DOC_VAULT_TOKEN (run tests via ./scripts/run_tests.sh)."
        )

    config = VaultConfig(url=vault_url, token=vault_token)
    return VaultClient(config)


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
    test_dir = tmp_path / "gofr-doc_test_data"
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
        storage.purge(age_days=0)  # Delete all documents
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
    Create an AuthService instance for testing with Vault stores.

    Uses VaultTokenStore and VaultGroupStore for isolation.
    Automatically creates reserved groups (public, admin) and TEST_GROUP.

    Returns:
        AuthService: Configured auth service with Vault stores
    """
    vault_client = _build_vault_client()
    path_prefix = f"gofr/tests/{uuid4()}"
    return _create_test_auth_service(vault_client, path_prefix)


@pytest.fixture(scope="function")
def test_jwt_token(test_auth_service):
    """
    Provide a valid JWT token for tests that require authentication.

    Token is created at test start and revoked at test end.

    Usage in tests:
        @pytest.mark.asyncio
        async def test_something(test_jwt_token):
            headers = {"Authorization": f"Bearer {test_jwt_token}"}
            # Use token in HTTP requests

    Returns:
        str: A valid JWT token for testing with 1 hour expiry
    """
    # Create token with 1 hour expiry
    token = test_auth_service.create_token(groups=[TEST_GROUP], expires_in_seconds=3600)

    yield token

    # Cleanup: revoke token after test
    try:
        test_auth_service.revoke_token(token)
    except Exception:
        pass  # Token may already be revoked or expired


# ============================================================================
# CONSOLIDATED AUTH FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def auth_service():
    """
    Create an isolated AuthService with Vault stores for each test.

    This is the standard fixture name used across most test files.
    Each test gets a fresh AuthService with no shared state.

    Returns:
        AuthService: Configured with TEST_JWT_SECRET and Vault stores
    """
    vault_client = _build_vault_client()
    path_prefix = f"gofr/tests/{uuid4()}"
    return _create_test_auth_service(vault_client, path_prefix)


@pytest.fixture(scope="function")
def mcp_headers(auth_service):
    """
    Provide pre-configured authentication headers for MCP server tests.

    Creates a token for 'test_group' with 1 hour expiry.

    Usage:
        async def test_mcp_endpoint(mcp_headers):
            async with MCPClient(MCP_URL) as client:
                result = await client.call_tool("tool_name", {...})
                # Headers automatically included

    Returns:
        Dict[str, str]: {"Authorization": "Bearer <token>"}
    """
    token = auth_service.create_token(groups=["test_group"], expires_in_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# SERVER-FACING AUTH FIXTURES (for integration tests)
# ============================================================================


@pytest.fixture(scope="session")
def server_auth_service():
    """
    Create an AuthService that shares the running server's Vault path.

    Unlike the per-test `auth_service` fixture (which uses a UUID-isolated
    Vault path), this fixture writes to the same path the MCP/web servers
    use (gofr/doc/auth).  Tokens created here are visible to the server.

    Use this (and `server_mcp_headers`) for integration tests that send
    requests to a live MCP or web server started by run_tests.sh.
    """
    vault_client = _build_vault_client()
    # The server's default path: prefix="GOFR_DOC" → "gofr/doc/auth"
    server_path = os.environ.get("GOFR_DOC_VAULT_PATH_PREFIX", "gofr/doc/auth")
    return _create_test_auth_service(vault_client, server_path)


@pytest.fixture(scope="function")
def server_mcp_headers(server_auth_service):
    """
    Auth headers recognised by the running MCP server.

    Creates a token in the server's Vault path (not the isolated test path).
    Use this for integration tests that call the live MCP server.
    """
    token = server_auth_service.create_token(groups=["test_group"], expires_in_seconds=3600)
    yield {"Authorization": f"Bearer {token}"}
    try:
        server_auth_service.revoke_token(token)
    except Exception:
        pass


@pytest.fixture(scope="function")
def server_web_headers(server_auth_service):
    """
    Auth headers recognised by the running web server.

    Creates a token in the server's Vault path (not the isolated test path).
    Use this for integration tests that call the live web server.
    """
    token = server_auth_service.create_token(groups=["test_group"], expires_in_seconds=3600)
    yield {"Authorization": f"Bearer {token}"}
    try:
        server_auth_service.revoke_token(token)
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def configure_test_auth_environment():
    """
    Configure environment variables for test server authentication.

    This ensures test MCP/web servers use the same Vault backend
    as the test fixtures. Auto-runs before all tests.
    """
    os.environ["GOFR_DOC_AUTH_BACKEND"] = "vault"

    # Default to local test vault if not already set
    vault_port = os.environ.get("GOFR_VAULT_PORT_TEST", "")
    default_vault_url = f"http://localhost:{vault_port}" if vault_port else ""
    if default_vault_url:
        os.environ.setdefault("GOFR_DOC_VAULT_URL", default_vault_url)
    os.environ.setdefault("GOFR_DOC_VAULT_TOKEN", "gofr-dev-root-token")

    yield

    # Cleanup
    os.environ.pop("GOFR_DOC_AUTH_BACKEND", None)
    os.environ.pop("GOFR_DOC_VAULT_URL", None)
    os.environ.pop("GOFR_DOC_VAULT_TOKEN", None)


# ============================================================================
# MOCK IMAGE SERVER FOR TESTING
# ============================================================================


@pytest.fixture(scope="function")
def image_server():
    """
    Provide a lightweight HTTP server for serving test images.

    The server serves files from test/mock/data directory on port 8765.
    Use image_server.get_url(filename) to get the full URL for a test image.
    In Docker mode, URLs use the dev container hostname (GOFR_DOC_IMAGE_SERVER_HOST)
    so MCP containers on the shared network can reach the server.

    Usage:
        def test_image_download(image_server):
            url = image_server.get_url("graph.png")
            # url is "http://gofr-doc-dev:8765/graph.png" (Docker mode)

    Returns:
        ImageServer: Server instance with start(), stop(), and get_url() methods
    """
    import sys
    from pathlib import Path

    # Add test directory to path for imports
    test_dir = Path(__file__).parent
    if str(test_dir) not in sys.path:
        sys.path.insert(0, str(test_dir))

    from mock.image_server import ImageServer

    server = ImageServer(port=8765)
    server.start()

    yield server

    server.stop()
