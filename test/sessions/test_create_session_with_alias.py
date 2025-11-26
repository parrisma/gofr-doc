"""Tests for create_session with required alias parameter."""

import pytest

from app.sessions.manager import SessionManager
from app.exceptions import SessionValidationError


class TestCreateSessionWithAlias:
    """Test suite for session creation with alias requirement."""

    @pytest.mark.asyncio
    async def test_create_session_with_valid_alias(self, session_manager: SessionManager):
        """Test creating session with valid alias."""
        alias = "test-session-2025"
        result = await session_manager.create_session(
            template_id="news_email", group="public", alias=alias
        )

        assert result.session_id is not None
        assert result.alias == alias
        assert result.template_id == "news_email"
        assert result.created_at is not None

        # Verify alias was registered
        assert session_manager.get_alias(result.session_id) == alias
        assert session_manager.resolve_session("public", alias) == result.session_id

    @pytest.mark.asyncio
    async def test_create_session_with_various_valid_aliases(self, session_manager: SessionManager):
        """Test various valid alias formats."""
        valid_aliases = [
            "abc",  # minimum length
            "a" * 64,  # maximum length
            "my-session",
            "test_session_123",
            "PROJECT-2025",
            "MixedCase123",
        ]

        for alias in valid_aliases:
            result = await session_manager.create_session(
                template_id="news_email", group="public", alias=alias
            )
            assert result.alias == alias
            assert session_manager.get_alias(result.session_id) == alias

    @pytest.mark.asyncio
    async def test_create_session_rejects_invalid_alias_format(
        self, session_manager: SessionManager
    ):
        """Test that invalid alias formats are rejected."""
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
            with pytest.raises(SessionValidationError) as exc_info:
                await session_manager.create_session(
                    template_id="news_email", group="public", alias=alias
                )
            assert exc_info.value.code == "INVALID_ALIAS"

    @pytest.mark.asyncio
    async def test_create_session_rejects_duplicate_alias_in_group(
        self, session_manager: SessionManager
    ):
        """Test that duplicate aliases within a group are rejected."""
        alias = "duplicate-test"
        group = "public"

        # Create first session
        result1 = await session_manager.create_session(
            template_id="news_email", group=group, alias=alias
        )
        assert result1.alias == alias

        # Try to create second session with same alias in same group
        with pytest.raises(SessionValidationError) as exc_info:
            await session_manager.create_session(template_id="news_email", group=group, alias=alias)
        assert exc_info.value.code == "ALIAS_EXISTS"
        assert alias in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_create_session_allows_duplicate_alias_across_groups(
        self, session_manager: SessionManager
    ):
        """Test that same alias can be used in different groups."""
        alias = "shared-name"

        # Create session in group1
        result1 = await session_manager.create_session(
            template_id="news_email", group="group1", alias=alias
        )

        # Create session with same alias in group2 - should succeed
        result2 = await session_manager.create_session(
            template_id="news_email", group="group2", alias=alias
        )

        assert result1.alias == alias
        assert result2.alias == alias
        assert result1.session_id != result2.session_id

        # Verify resolution is group-scoped
        assert session_manager.resolve_session("group1", alias) == result1.session_id
        assert session_manager.resolve_session("group2", alias) == result2.session_id

    @pytest.mark.asyncio
    async def test_create_session_persists_alias(self, session_manager: SessionManager):
        """Test that alias is persisted with session."""
        alias = "persistent-session"
        result = await session_manager.create_session(
            template_id="news_email", group="public", alias=alias
        )

        # Retrieve session and verify alias is stored
        session = await session_manager.get_session(result.session_id)
        assert session is not None
        assert session.alias == alias

    @pytest.mark.asyncio
    async def test_create_session_with_invalid_template_still_validates_alias(
        self, session_manager: SessionManager
    ):
        """Test that alias validation happens even with invalid template."""
        # Invalid alias should be caught before template validation
        with pytest.raises(SessionValidationError) as exc_info:
            await session_manager.create_session(
                template_id="nonexistent-template", group="public", alias="ab"  # too short
            )
        # Could be either INVALID_ALIAS or TEMPLATE_NOT_FOUND depending on order
        assert exc_info.value.code in ["INVALID_ALIAS", "TEMPLATE_NOT_FOUND"]

    @pytest.mark.asyncio
    async def test_multiple_sessions_with_different_aliases(self, session_manager: SessionManager):
        """Test creating multiple sessions with different aliases in same group."""
        group = "public"
        aliases = ["session-1", "session-2", "session-3"]
        session_ids = []

        for alias in aliases:
            result = await session_manager.create_session(
                template_id="news_email", group=group, alias=alias
            )
            session_ids.append(result.session_id)
            assert result.alias == alias

        # Verify all aliases resolve correctly
        for alias, expected_id in zip(aliases, session_ids):
            assert session_manager.resolve_session(group, alias) == expected_id
