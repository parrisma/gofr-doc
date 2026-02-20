"""Theme registry.

Provides visual themes (light, dark, bizlight, bizdark) and a registry
for looking them up by name.
"""

from typing import Dict

from app.plot.themes.base import Theme
from app.plot.themes.light import LightTheme
from app.plot.themes.dark import DarkTheme
from app.plot.themes.bizlight import BizLightTheme
from app.plot.themes.bizdark import BizDarkTheme

# Registry of available themes
_THEMES: Dict[str, Theme] = {
    "light": LightTheme(),
    "dark": DarkTheme(),
    "bizlight": BizLightTheme(),
    "bizdark": BizDarkTheme(),
}


def get_theme(name: str = "light") -> Theme:
    """Get a theme by name.

    Args:
        name: Theme name (light, dark, bizlight, bizdark)

    Returns:
        Theme instance

    Raises:
        ValueError: If theme name is not found
    """
    theme_name = name.lower() if name else "light"
    theme = _THEMES.get(theme_name)
    if theme is None:
        available = ", ".join(_THEMES.keys())
        raise ValueError(f"Unknown theme '{name}'. Available themes: {available}")
    return theme


def list_themes() -> list[str]:
    """Get a list of available theme names."""
    return list(_THEMES.keys())


def list_themes_with_descriptions() -> Dict[str, str]:
    """Get a dictionary of theme names to their descriptions."""
    return {name: theme.get_description() for name, theme in _THEMES.items()}


__all__ = [
    "Theme",
    "LightTheme",
    "DarkTheme",
    "BizLightTheme",
    "BizDarkTheme",
    "get_theme",
    "list_themes",
    "list_themes_with_descriptions",
]
