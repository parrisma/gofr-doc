"""Tests for session aliasing functionality."""

import uuid
from pathlib import Path

import pytest

from app.sessions.manager import SessionManager
from app.sessions.storage import SessionStore
from app.templates.registry import TemplateRegistry
from app.logger import ConsoleLogger


@pytest.fixture
def session_manager(tmp_path):
    """Create a SessionManager instance for testing."""
    # Create session storage
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    session_store = SessionStore(str(sessions_dir))

    # Create logger
    logger = ConsoleLogger()

    # Create template registry
    templates_dir = Path(__file__).parent.parent / "data" / "templates"
    template_registry = TemplateRegistry(
        templates_dir=str(templates_dir), group="test-group", logger=logger
    )

    # Create and return session manager
    return SessionManager(
        session_store=session_store, template_registry=template_registry, logger=logger
    )


class TestSessionAliasing:
    """Test suite for session aliasing core functionality."""

    def test_alias_validation_valid(self, session_manager: SessionManager):
        """Test that valid aliases are accepted."""
        valid_aliases = [
            "my-session",
            "test_session_123",
            "PROJECT-2024",
            "abc",  # minimum length
            "a" * 64,  # maximum length
            "MixedCase123",
        ]
        for alias in valid_aliases:
            assert session_manager._is_valid_alias(alias), f"Expected '{alias}' to be valid"

    def test_alias_validation_invalid(self, session_manager: SessionManager):
        """Test that invalid aliases are rejected."""
        invalid_aliases = [
            "ab",  # too short
            "a" * 65,  # too long
            "has spaces",
            "has@special",
            "has.dots",
            "",
            "has/slash",
            "has\\backslash",
        ]
        for alias in invalid_aliases:
            assert not session_manager._is_valid_alias(alias), f"Expected '{alias}' to be invalid"

    def test_uuid_validation(self, session_manager: SessionManager):
        """Test UUID validation."""
        valid_guid = str(uuid.uuid4())
        assert session_manager._is_valid_uuid(valid_guid)

        invalid_guids = [
            "not-a-uuid",
            "12345",
            "",
            "test-session",
        ]
        for invalid in invalid_guids:
            assert not session_manager._is_valid_uuid(invalid)

    def test_alias_registration(self, session_manager: SessionManager):
        """Test registering an alias."""
        group = "test-group"
        alias = "my-test-session"
        session_id = str(uuid.uuid4())

        session_manager._register_alias(group, alias, session_id)

        # Check forward mapping
        assert group in session_manager._alias_to_guid
        assert alias in session_manager._alias_to_guid[group]
        assert session_manager._alias_to_guid[group][alias] == session_id

        # Check reverse mapping
        assert session_id in session_manager._guid_to_alias
        assert session_manager._guid_to_alias[session_id] == alias

    def test_alias_unregistration(self, session_manager: SessionManager):
        """Test unregistering an alias."""
        group = "test-group"
        alias = "temp-session"
        session_id = str(uuid.uuid4())

        # Register first
        session_manager._register_alias(group, alias, session_id)
        assert session_manager.get_alias(session_id) == alias

        # Unregister
        session_manager._unregister_alias(session_id)

        # Verify removal
        assert session_manager.get_alias(session_id) is None
        if group in session_manager._alias_to_guid:
            assert alias not in session_manager._alias_to_guid[group]

    def test_resolve_session_by_alias(self, session_manager: SessionManager):
        """Test resolving session by alias."""
        group = "test-group"
        alias = "my-session"
        session_id = str(uuid.uuid4())

        session_manager._register_alias(group, alias, session_id)

        resolved = session_manager.resolve_session(group, alias)
        assert resolved == session_id

    def test_resolve_session_by_guid(self, session_manager: SessionManager):
        """Test resolving session by GUID."""
        group = "test-group"
        session_id = str(uuid.uuid4())

        resolved = session_manager.resolve_session(group, session_id)
        assert resolved == session_id

    def test_resolve_session_invalid(self, session_manager: SessionManager):
        """Test resolving with invalid identifier."""
        group = "test-group"

        # Non-existent alias
        resolved = session_manager.resolve_session(group, "nonexistent-alias")
        assert resolved is None

        # Invalid format
        resolved = session_manager.resolve_session(group, "not a valid identifier!")
        assert resolved is None

    def test_resolve_session_wrong_group(self, session_manager: SessionManager):
        """Test that alias resolution is group-scoped."""
        group1 = "group1"
        group2 = "group2"
        alias = "shared-name"
        session_id = str(uuid.uuid4())

        # Register in group1
        session_manager._register_alias(group1, alias, session_id)

        # Resolve in group1 - should work
        assert session_manager.resolve_session(group1, alias) == session_id

        # Resolve in group2 - should fail
        assert session_manager.resolve_session(group2, alias) is None

    def test_get_alias_by_guid(self, session_manager: SessionManager):
        """Test retrieving alias by GUID."""
        group = "test-group"
        alias = "my-session"
        session_id = str(uuid.uuid4())

        # Before registration
        assert session_manager.get_alias(session_id) is None

        # After registration
        session_manager._register_alias(group, alias, session_id)
        assert session_manager.get_alias(session_id) == alias

    def test_alias_uniqueness_per_group(self, session_manager: SessionManager):
        """Test that aliases can be reused across groups but not within a group."""
        alias = "duplicate-name"
        group1 = "group1"
        group2 = "group2"
        session_id1 = str(uuid.uuid4())
        session_id2 = str(uuid.uuid4())

        # Register same alias in two different groups
        session_manager._register_alias(group1, alias, session_id1)
        session_manager._register_alias(group2, alias, session_id2)

        # Each should resolve to different sessions
        assert session_manager.resolve_session(group1, alias) == session_id1
        assert session_manager.resolve_session(group2, alias) == session_id2

    def test_multiple_aliases_different_groups(self, session_manager: SessionManager):
        """Test managing multiple aliases across groups."""
        aliases_data = [
            ("group1", "session-a", str(uuid.uuid4())),
            ("group1", "session-b", str(uuid.uuid4())),
            ("group2", "session-c", str(uuid.uuid4())),
            ("group2", "session-d", str(uuid.uuid4())),
        ]

        # Register all
        for group, alias, session_id in aliases_data:
            session_manager._register_alias(group, alias, session_id)

        # Verify all resolve correctly
        for group, alias, expected_id in aliases_data:
            assert session_manager.resolve_session(group, alias) == expected_id
            assert session_manager.get_alias(expected_id) == alias
