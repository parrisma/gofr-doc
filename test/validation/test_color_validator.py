"""Tests for color validation."""

import pytest

from app.validation.color_validator import (
    ColorValidationError,
    THEME_COLORS,
    validate_color,
    validate_theme_color,
    validate_hex_color,
    get_css_color,
)


class TestThemeColorValidation:
    """Tests for theme color validation."""

    def test_valid_theme_colors(self):
        """Test all valid theme colors."""
        for color in THEME_COLORS:
            assert validate_theme_color(color) is True
            assert validate_color(color) is True

    def test_blue_theme_color(self):
        """Test blue theme color."""
        assert validate_theme_color("blue") is True
        assert validate_color("blue") is True

    def test_orange_theme_color(self):
        """Test orange theme color."""
        assert validate_theme_color("orange") is True
        assert validate_color("orange") is True

    def test_green_theme_color(self):
        """Test green theme color."""
        assert validate_theme_color("green") is True
        assert validate_color("green") is True

    def test_red_theme_color(self):
        """Test red theme color."""
        assert validate_theme_color("red") is True
        assert validate_color("red") is True

    def test_purple_theme_color(self):
        """Test purple theme color."""
        assert validate_theme_color("purple") is True
        assert validate_color("purple") is True

    def test_brown_theme_color(self):
        """Test brown theme color."""
        assert validate_theme_color("brown") is True
        assert validate_color("brown") is True

    def test_pink_theme_color(self):
        """Test pink theme color."""
        assert validate_theme_color("pink") is True
        assert validate_color("pink") is True

    def test_gray_theme_color(self):
        """Test gray theme color."""
        assert validate_theme_color("gray") is True
        assert validate_color("gray") is True

    def test_invalid_theme_color(self):
        """Test invalid theme color name."""
        assert validate_theme_color("invalid") is False
        assert validate_theme_color("yellow") is False

    def test_case_insensitive(self):
        """Test theme colors are case-insensitive."""
        assert validate_theme_color("BLUE") is True
        assert validate_theme_color("Blue") is True
        assert validate_theme_color("blue") is True

    def test_theme_color_with_whitespace(self):
        """Test theme color with whitespace."""
        assert validate_theme_color(" blue ") is True
        assert validate_theme_color("  green  ") is True


class TestHexColorValidation:
    """Tests for hex color validation."""

    def test_valid_6_digit_hex(self):
        """Test valid 6-digit hex colors."""
        assert validate_hex_color("#FF0000") is True
        assert validate_hex_color("#00FF00") is True
        assert validate_hex_color("#0000FF") is True
        assert validate_hex_color("#123456") is True

    def test_valid_3_digit_hex(self):
        """Test valid 3-digit hex colors."""
        assert validate_hex_color("#F00") is True
        assert validate_hex_color("#0F0") is True
        assert validate_hex_color("#00F") is True
        assert validate_hex_color("#ABC") is True

    def test_lowercase_hex(self):
        """Test lowercase hex colors."""
        assert validate_hex_color("#ff0000") is True
        assert validate_hex_color("#abc123") is True
        assert validate_hex_color("#f0f") is True

    def test_mixed_case_hex(self):
        """Test mixed case hex colors."""
        assert validate_hex_color("#Ff0000") is True
        assert validate_hex_color("#AbC123") is True

    def test_invalid_hex_no_hash(self):
        """Test hex color without # is invalid."""
        assert validate_hex_color("FF0000") is False
        assert validate_hex_color("F00") is False

    def test_invalid_hex_length(self):
        """Test invalid hex color lengths."""
        assert validate_hex_color("#FF") is False
        assert validate_hex_color("#FFFF") is False
        assert validate_hex_color("#FFFFF") is False
        assert validate_hex_color("#FFFFFFF") is False

    def test_invalid_hex_characters(self):
        """Test hex colors with invalid characters."""
        assert validate_hex_color("#GGGGGG") is False
        assert validate_hex_color("#ZZZ") is False
        assert validate_hex_color("#FF00GG") is False

    def test_empty_hex_color(self):
        """Test empty hex color."""
        assert validate_hex_color("") is False
        assert validate_hex_color("#") is False


class TestGeneralColorValidation:
    """Tests for general color validation."""

    def test_none_color_is_valid(self):
        """Test None is considered valid."""
        assert validate_color(None) is True

    def test_empty_string_is_valid(self):
        """Test empty string is considered valid."""
        assert validate_color("") is True
        assert validate_color("  ") is True

    def test_theme_color_validation(self):
        """Test theme colors pass general validation."""
        assert validate_color("blue") is True
        assert validate_color("red") is True

    def test_hex_color_validation(self):
        """Test hex colors pass general validation."""
        assert validate_color("#FF0000") is True
        assert validate_color("#ABC") is True

    def test_invalid_color_format(self):
        """Test invalid color formats."""
        assert validate_color("invalid") is False
        assert validate_color("rgb(255,0,0)") is False
        assert validate_color("255") is False


class TestCSSColorGeneration:
    """Tests for CSS color generation."""

    def test_theme_color_to_css(self):
        """Test theme color converts to CSS variable."""
        result = get_css_color("blue")
        assert "var(--gofr-doc-blue" in result

    def test_all_theme_colors_to_css(self):
        """Test all theme colors convert to CSS."""
        for color in THEME_COLORS:
            result = get_css_color(color)
            assert "var(--gofr-doc-" in result
            assert color in result

    def test_hex_color_to_css(self):
        """Test hex color returns as-is."""
        assert get_css_color("#FF0000") == "#FF0000"
        assert get_css_color("#ABC") == "#ABC"

    def test_case_insensitive_theme_css(self):
        """Test case-insensitive theme color to CSS."""
        result1 = get_css_color("blue")
        result2 = get_css_color("BLUE")
        result3 = get_css_color("Blue")
        # All should produce same CSS variable reference
        assert "blue" in result1.lower()
        assert "blue" in result2.lower()
        assert "blue" in result3.lower()

    def test_invalid_color_raises_error(self):
        """Test invalid color raises error."""
        with pytest.raises(ColorValidationError):
            get_css_color("invalid")

        with pytest.raises(ColorValidationError):
            get_css_color("rgb(255,0,0)")

    def test_css_variable_fallback(self):
        """Test CSS variable includes fallback."""
        result = get_css_color("blue")
        assert "var(--gofr-doc-blue" in result
        # Should have fallback value after comma
        assert "," in result
