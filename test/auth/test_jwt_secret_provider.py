"""Unit tests for JwtSecretProvider.

Uses a mock VaultClient -- no real Vault needed.
"""

import hashlib
import threading
from unittest.mock import MagicMock

import pytest

from gofr_common.auth.jwt_secret_provider import JwtSecretProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_vault(secret_value: str = "test-secret-42") -> MagicMock:
    """Return a mock VaultClient whose read_secret returns ``{value: ...}``."""
    client = MagicMock()
    client.read_secret.return_value = {"value": secret_value}
    return client


def _fingerprint(secret: str) -> str:
    digest = hashlib.sha256(secret.encode()).hexdigest()
    return f"sha256:{digest[:12]}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestJwtSecretProvider:
    """Core provider behaviour."""

    def test_first_get_reads_from_vault(self):
        """First call to get() must hit Vault."""
        client = _make_mock_vault("my-secret")
        provider = JwtSecretProvider(client, cache_ttl_seconds=300)

        result = provider.get()

        assert result == "my-secret"
        client.read_secret.assert_called_once_with("gofr/config/jwt-signing-secret")

    def test_second_get_within_ttl_uses_cache(self):
        """A second get() inside the TTL window must NOT call Vault again."""
        client = _make_mock_vault("cached-secret")
        provider = JwtSecretProvider(client, cache_ttl_seconds=300)

        provider.get()
        provider.get()

        assert client.read_secret.call_count == 1

    def test_get_after_ttl_rereads(self):
        """After TTL expires, get() must re-read from Vault."""
        client = _make_mock_vault("secret-v1")
        provider = JwtSecretProvider(client, cache_ttl_seconds=1)

        provider.get()
        assert client.read_secret.call_count == 1

        # Force TTL expiry
        provider._cache_expires_at = 0.0

        provider.get()
        assert client.read_secret.call_count == 2

    def test_fingerprint_matches_sha256(self):
        """fingerprint property must return sha256:<first12> of the secret."""
        client = _make_mock_vault("fingerprint-test")
        provider = JwtSecretProvider(client, cache_ttl_seconds=300)

        assert provider.fingerprint == _fingerprint("fingerprint-test")

    def test_rotation_logged_at_warning(self):
        """When the secret changes on refresh, a WARNING must be logged."""
        client = MagicMock()
        client.read_secret.side_effect = [
            {"value": "secret-v1"},
            {"value": "secret-v2"},
        ]
        logger = MagicMock()

        provider = JwtSecretProvider(client, cache_ttl_seconds=1, logger=logger)
        provider.get()

        # Force TTL expiry
        provider._cache_expires_at = 0.0
        result = provider.get()

        assert result == "secret-v2"
        logger.warning.assert_called_once()
        call_kwargs = logger.warning.call_args
        assert "rotated" in call_kwargs[0][0].lower() or "rotated" in str(call_kwargs)

    def test_invalidate_forces_reread(self):
        """invalidate() must cause the next get() to read from Vault."""
        client = _make_mock_vault("invalidate-test")
        provider = JwtSecretProvider(client, cache_ttl_seconds=300)

        provider.get()
        assert client.read_secret.call_count == 1

        provider.invalidate()
        provider.get()
        assert client.read_secret.call_count == 2

    def test_vault_read_failure_raises(self):
        """If Vault returns None, get() must raise RuntimeError."""
        client = MagicMock()
        client.read_secret.return_value = None

        provider = JwtSecretProvider(client, cache_ttl_seconds=300)

        with pytest.raises(RuntimeError, match="JWT secret not found"):
            provider.get()

    def test_vault_missing_value_key_raises(self):
        """If Vault data has no 'value' key, get() must raise RuntimeError."""
        client = MagicMock()
        client.read_secret.return_value = {"wrong_key": "oops"}

        provider = JwtSecretProvider(client, cache_ttl_seconds=300)

        with pytest.raises(RuntimeError, match="missing 'value' key"):
            provider.get()

    def test_vault_exception_propagates(self):
        """Vault client exceptions must propagate (not be swallowed)."""
        client = MagicMock()
        client.read_secret.side_effect = ConnectionError("Vault unreachable")

        provider = JwtSecretProvider(client, cache_ttl_seconds=300)

        with pytest.raises(ConnectionError, match="Vault unreachable"):
            provider.get()

    def test_custom_vault_path(self):
        """Provider must use the vault_path passed at construction."""
        client = _make_mock_vault("custom-path")
        provider = JwtSecretProvider(
            client,
            vault_path="custom/jwt/path",
            cache_ttl_seconds=300,
        )

        provider.get()
        client.read_secret.assert_called_once_with("custom/jwt/path")


class TestThreadSafety:
    """Concurrent access must not corrupt state."""

    def test_concurrent_gets(self):
        """Multiple threads calling get() simultaneously must all succeed."""
        client = _make_mock_vault("thread-safe-secret")
        provider = JwtSecretProvider(client, cache_ttl_seconds=300)

        results = []
        errors = []

        def worker():
            try:
                results.append(provider.get())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(errors) == 0, f"Errors in threads: {errors}"
        assert all(r == "thread-safe-secret" for r in results)
        # Only one Vault read should have happened (all others hit cache)
        assert client.read_secret.call_count == 1
