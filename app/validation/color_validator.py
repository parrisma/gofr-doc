"""Color validation for table styling.

Validates theme color names and custom hex colors.
"""

import re
from typing import Optional, Dict, Any

from app.exceptions import ValidationError


class ColorValidationError(ValidationError):
    """Raised when color validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(code="INVALID_COLOR", message=message, details=details)


# Valid theme color names (map to CSS variables)
# Includes both basic colors and Bootstrap-style semantic colors
THEME_COLORS = {
    "blue",
    "orange",
    "green",
    "red",
    "purple",
    "brown",
    "pink",
    "gray",
    # Bootstrap-style semantic colors
    "primary",
    "success",
    "warning",
    "danger",
    "info",
    "light",
    "dark",
    "muted",
}


def validate_color(color: Optional[str]) -> bool:
    """Validate a color value.

    Args:
        color: Color value (theme name or hex code)

    Returns:
        True if valid, False otherwise
    """
    if not color or not color.strip():
        return True

    color = color.strip().lower()

    # Check if it's a theme color
    if color in THEME_COLORS:
        return True

    # Check if it's a valid hex color (#RRGGBB or #RGB)
    if color.startswith("#"):
        hex_pattern = r"^#([0-9a-f]{3}|[0-9a-f]{6})$"
        return bool(re.match(hex_pattern, color, re.IGNORECASE))

    return False


def validate_theme_color(color: str) -> bool:
    """Validate that color is a theme color name.

    Args:
        color: Color name to validate

    Returns:
        True if valid theme color, False otherwise
    """
    if not color:
        return False

    return color.strip().lower() in THEME_COLORS


def validate_hex_color(color: str) -> bool:
    """Validate that color is a valid hex color code.

    Args:
        color: Hex color code to validate (e.g., "#FF0000" or "#F00")

    Returns:
        True if valid hex color, False otherwise
    """
    if not color:
        return False

    color = color.strip()
    if not color.startswith("#"):
        return False

    hex_pattern = r"^#([0-9a-f]{3}|[0-9a-f]{6})$"
    return bool(re.match(hex_pattern, color, re.IGNORECASE))


def get_css_color(color: str) -> str:
    """Convert color to CSS value.

    Args:
        color: Theme color name or hex color

    Returns:
        CSS color value (CSS variable or hex code)

    Raises:
        ColorValidationError: If color is invalid
    """
    if not validate_color(color):
        raise ColorValidationError(f"Invalid color: {color}")

    color_lower = color.strip().lower()

    # Theme color - return CSS variable
    if color_lower in THEME_COLORS:
        return f"var(--gofr-doc-{color_lower}, #{color_lower})"

    # Hex color - return as-is
    if color.startswith("#"):
        return color

    raise ColorValidationError(f"Invalid color format: {color}")
