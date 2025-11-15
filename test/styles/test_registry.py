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