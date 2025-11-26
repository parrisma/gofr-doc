"""Pytest fixtures for session tests."""

import pytest
from pathlib import Path

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

    # Use actual test data directory for templates
    project_root = Path(__file__).parent.parent.parent
    templates_dir = project_root / "test" / "data" / "docs" / "templates"

    # Load templates from all groups (public, group1, group2)
    template_registry = TemplateRegistry(
        templates_dir=str(templates_dir), groups=["public", "group1", "group2"], logger=logger
    )  # Create and return session manager
    return SessionManager(
        session_store=session_store, template_registry=template_registry, logger=logger
    )
