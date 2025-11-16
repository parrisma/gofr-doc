"""Unit tests for app.styles.registry.StyleRegistry."""
from __future__ import annotations

from pathlib import Path
from typing import Any, List, Tuple

import pytest

from app.logger import DefaultLogger
from app.styles.registry import StyleRegistry


@pytest.fixture
def mock_styles_dir() -> Path:
    """Absolute path to the bundled mock styles directory."""
    return Path(__file__).parent / "mock_styles"


@pytest.fixture
def mock_logger() -> DefaultLogger:
    return DefaultLogger()


@pytest.fixture
def style_registry(mock_styles_dir: Path, mock_logger: DefaultLogger) -> StyleRegistry:
    return StyleRegistry(str(mock_styles_dir), mock_logger)


# ============================================================================
# BASIC FUNCTIONALITY TESTS
# ============================================================================

def test_list_styles_returns_available_styles(style_registry: StyleRegistry) -> None:
    styles = style_registry.list_styles()
    style_ids = {item.style_id for item in styles}

    assert style_ids == {"primary", "alternate"}


def test_get_style_metadata_and_css(style_registry: StyleRegistry) -> None:
    metadata = style_registry.get_style_metadata("primary")
    assert metadata is not None
    assert metadata.name == "Primary Mock Style"
    assert metadata.description.startswith("Primary style")

    css = style_registry.get_style_css("primary")
    assert css is not None
    assert "background" in css


def test_style_exists_handles_valid_and_missing(style_registry: StyleRegistry) -> None:
    assert style_registry.style_exists("primary") is True
    assert style_registry.style_exists("alternate") is True
    assert style_registry.style_exists("missing") is False


def test_missing_files_are_skipped(style_registry: StyleRegistry) -> None:
    assert style_registry.get_style_metadata("missing") is None


def test_default_css_matches_selected_style(style_registry: StyleRegistry) -> None:
    default_style_id = style_registry.get_default_style_id()
    assert default_style_id in {"primary", "alternate"}

    default_css = style_registry.get_default_css()
    assert default_css == style_registry.get_style_css(default_style_id)


def test_empty_styles_directory_has_no_default(tmp_path: Path, mock_logger: DefaultLogger) -> None:
    empty_dir = tmp_path / "no_styles"
    empty_dir.mkdir()

    registry = StyleRegistry(str(empty_dir), mock_logger)

    assert registry.list_styles() == []
    assert registry.get_default_style_id() is None
    assert registry.get_default_css() == ""


# ============================================================================
# GROUP FUNCTIONALITY TESTS
# ============================================================================

def test_list_groups_returns_public_group(style_registry: StyleRegistry) -> None:
    """Test that list_groups discovers available groups."""
    groups = style_registry.list_groups()
    assert "public" in groups
    assert len(groups) >= 1


def test_list_styles_with_group_filter(style_registry: StyleRegistry) -> None:
    """Test filtering styles by group."""
    # List all styles
    all_styles = style_registry.list_styles()
    assert len(all_styles) >= 2
    
    # Filter by public group
    public_styles = style_registry.list_styles(group="public")
    
    # Public should have all styles (since only public group exists in mock)
    assert len(public_styles) == len(all_styles)
    # All styles should be from public group
    assert all(s.group == "public" for s in public_styles)


def test_style_metadata_includes_group(style_registry: StyleRegistry) -> None:
    """Test that style metadata includes group field."""
    metadata = style_registry.get_style_metadata("primary")
    
    assert metadata is not None
    assert hasattr(metadata, "group")
    assert metadata.group == "public"


def test_list_styles_response_includes_group(style_registry: StyleRegistry) -> None:
    """Test that list_styles response includes group information."""
    styles = style_registry.list_styles()
    
    assert len(styles) > 0
    # All items should have group field
    for style in styles:
        assert hasattr(style, "group")
        assert style.group == "public"
        assert style.style_id in {"primary", "alternate"}


def test_get_items_by_group_organizes_styles(style_registry: StyleRegistry) -> None:
    """Test get_items_by_group returns styles organized by group."""
    items_by_group = style_registry.get_items_by_group()
    
    # Should have public group
    assert "public" in items_by_group
    
    # Public group should have items
    public_items = items_by_group["public"]
    assert len(public_items) >= 2
    
    # All items in public group should have correct group
    for item in public_items:
        assert hasattr(item, "group")
        assert item.group == "public"
        assert hasattr(item, "style_id")


def test_single_group_registry_with_group_parameter(
    mock_styles_dir: Path, mock_logger: DefaultLogger
) -> None:
    """Test creating registry with specific group filter."""
    registry = StyleRegistry(str(mock_styles_dir), mock_logger, group="public")
    
    styles = registry.list_styles()
    
    # Should only get styles from public group
    assert len(styles) >= 2
    assert all(s.group == "public" for s in styles)


def test_multiple_groups_registry_with_groups_parameter(
    mock_styles_dir: Path, mock_logger: DefaultLogger
) -> None:
    """Test creating registry with multiple groups."""
    registry = StyleRegistry(str(mock_styles_dir), mock_logger, groups=["public"])
    
    groups = registry.list_groups()
    
    # Should discover specified groups
    assert "public" in groups
    
    styles = registry.list_styles()
    assert len(styles) >= 2
    assert all(s.group == "public" for s in styles)
