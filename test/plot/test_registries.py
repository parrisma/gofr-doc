"""Tests for plot registries -- handler and theme discovery."""

import pytest

from app.plot.handlers import (
    get_handler,
    list_handlers,
    list_handlers_with_descriptions,
)
from app.plot.themes import (
    get_theme,
    list_themes,
    list_themes_with_descriptions,
)


class TestHandlerRegistry:
    """Handler registry discovery tests."""

    def test_list_handlers_returns_expected_types(self):
        handlers = list_handlers()
        assert "line" in handlers
        assert "scatter" in handlers
        assert "bar" in handlers

    def test_list_handlers_count(self):
        handlers = list_handlers()
        assert len(handlers) == 3

    def test_get_handler_line(self):
        handler = get_handler("line")
        assert handler is not None
        assert hasattr(handler, "plot")

    def test_get_handler_scatter(self):
        handler = get_handler("scatter")
        assert handler is not None
        assert hasattr(handler, "plot")

    def test_get_handler_bar(self):
        handler = get_handler("bar")
        assert handler is not None
        assert hasattr(handler, "plot")

    def test_get_handler_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown handler"):
            get_handler("pie")

    def test_list_handlers_with_descriptions(self):
        descs = list_handlers_with_descriptions()
        assert isinstance(descs, dict)
        assert len(descs) == 3
        for name, description in descs.items():
            assert isinstance(name, str)
            assert isinstance(description, str)
            assert len(description) > 0


class TestThemeRegistry:
    """Theme registry discovery tests."""

    def test_list_themes_returns_expected(self):
        themes = list_themes()
        assert "light" in themes
        assert "dark" in themes
        assert "bizlight" in themes
        assert "bizdark" in themes

    def test_list_themes_count(self):
        themes = list_themes()
        assert len(themes) == 4

    def test_get_theme_light(self):
        theme = get_theme("light")
        assert theme is not None
        assert hasattr(theme, "apply")
        assert hasattr(theme, "get_default_color")

    def test_get_theme_dark(self):
        theme = get_theme("dark")
        assert theme is not None

    def test_get_theme_bizlight(self):
        theme = get_theme("bizlight")
        assert theme is not None

    def test_get_theme_bizdark(self):
        theme = get_theme("bizdark")
        assert theme is not None

    def test_get_theme_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown theme"):
            get_theme("neon")

    def test_list_themes_with_descriptions(self):
        descs = list_themes_with_descriptions()
        assert isinstance(descs, dict)
        assert len(descs) == 4
        for name, description in descs.items():
            assert isinstance(name, str)
            assert isinstance(description, str)
            assert len(description) > 0

    def test_theme_default_color_is_string(self):
        for name in list_themes():
            theme = get_theme(name)
            color = theme.get_default_color()
            assert isinstance(color, str)
            assert len(color) > 0
