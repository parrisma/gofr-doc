"""Tests for number formatting."""

import pytest
from decimal import Decimal

from app.formatting.number_formatter import (
    NumberFormatError,
    format_number,
    validate_format_spec,
)


class TestCurrencyFormatting:
    """Tests for currency formatting."""

    def test_format_usd(self):
        """Test USD currency formatting."""
        result = format_number(1234.56, "currency:USD")
        assert "$1,234.56" in result

    def test_format_eur(self):
        """Test EUR currency formatting."""
        result = format_number(1234.56, "currency:EUR")
        assert "1,234.56" in result
        assert "€" in result

    def test_format_gbp(self):
        """Test GBP currency formatting."""
        result = format_number(1234.56, "currency:GBP")
        assert "1,234.56" in result
        assert "£" in result

    def test_format_jpy(self):
        """Test JPY currency formatting (no decimals)."""
        result = format_number(1234, "currency:JPY")
        assert "¥1,234" in result or "JPY" in result

    def test_currency_negative(self):
        """Test negative currency formatting."""
        result = format_number(-1234.56, "currency:USD")
        assert "-$1,234.56" in result or "($1,234.56)" in result

    def test_invalid_currency_code(self):
        """Test invalid currency code."""
        with pytest.raises(NumberFormatError):
            format_number(100, "currency:INVALID")


class TestPercentFormatting:
    """Tests for percentage formatting."""

    def test_format_percent(self):
        """Test percentage formatting."""
        result = format_number(0.15, "percent")
        assert "15" in result
        assert "%" in result

    def test_format_percent_decimal(self):
        """Test percentage with decimal."""
        result = format_number(0.1234, "percent")
        assert "12" in result
        assert "%" in result

    def test_format_percent_whole(self):
        """Test percentage from whole number."""
        result = format_number(1, "percent")
        assert "100" in result
        assert "%" in result

    def test_format_percent_negative(self):
        """Test negative percentage."""
        result = format_number(-0.25, "percent")
        assert "-25" in result or "(25" in result
        assert "%" in result


class TestDecimalFormatting:
    """Tests for decimal formatting."""

    def test_format_decimal_2(self):
        """Test decimal with 2 places."""
        result = format_number(1234.5678, "decimal:2")
        assert "1,234.57" in result

    def test_format_decimal_0(self):
        """Test decimal with 0 places (integer)."""
        result = format_number(1234.5678, "decimal:0")
        assert "1,235" in result
        assert "." not in result

    def test_format_decimal_4(self):
        """Test decimal with 4 places."""
        result = format_number(1234.5678, "decimal:4")
        assert "1,234.5678" in result

    def test_format_decimal_rounding(self):
        """Test decimal rounding."""
        result = format_number(1234.555, "decimal:2")
        assert "1,234.56" in result or "1,234.55" in result  # Rounding may vary

    def test_invalid_decimal_format(self):
        """Test invalid decimal format."""
        with pytest.raises(NumberFormatError):
            format_number(100, "decimal:abc")


class TestIntegerFormatting:
    """Tests for integer formatting."""

    def test_format_integer(self):
        """Test integer formatting."""
        result = format_number(1234.5678, "integer")
        assert "1,235" in result
        assert "." not in result

    def test_format_integer_whole(self):
        """Test integer formatting of whole number."""
        result = format_number(1234, "integer")
        assert "1,234" in result

    def test_format_integer_negative(self):
        """Test negative integer formatting."""
        result = format_number(-1234, "integer")
        assert "-1,234" in result or "(1,234)" in result


class TestAccountingFormatting:
    """Tests for accounting format (parentheses for negatives)."""

    def test_format_accounting_positive(self):
        """Test accounting format for positive number."""
        result = format_number(1234.56, "accounting")
        assert "1,234.56" in result
        assert "(" not in result

    def test_format_accounting_negative(self):
        """Test accounting format for negative number."""
        result = format_number(-1234.56, "accounting")
        assert "(1,234.56)" in result
        assert "-" not in result

    def test_format_accounting_zero(self):
        """Test accounting format for zero."""
        result = format_number(0, "accounting")
        assert "0.00" in result


class TestValueHandling:
    """Tests for handling different value types."""

    def test_format_none(self):
        """Test formatting None returns empty string."""
        result = format_number(None, "currency:USD")
        assert result == ""

    def test_format_empty_string(self):
        """Test formatting empty string returns empty."""
        result = format_number("", "currency:USD")
        assert result == ""

    def test_format_string_number(self):
        """Test formatting string that contains number."""
        result = format_number("1234.56", "currency:USD")
        assert "$1,234.56" in result

    def test_format_string_with_commas(self):
        """Test formatting string with commas."""
        result = format_number("1,234.56", "decimal:2")
        assert "1,234.56" in result

    def test_format_non_numeric_string(self):
        """Test formatting non-numeric string returns as-is."""
        result = format_number("Not a number", "currency:USD")
        assert result == "Not a number"

    def test_format_no_spec(self):
        """Test formatting with no spec returns string value."""
        result = format_number(1234.56, None)
        assert "1234.56" in result

    def test_format_decimal_type(self):
        """Test formatting Decimal type."""
        result = format_number(Decimal("1234.56"), "currency:USD")
        assert "$1,234.56" in result


class TestFormatValidation:
    """Tests for format specification validation."""

    def test_validate_currency_format(self):
        """Test currency format validation."""
        assert validate_format_spec("currency:USD") is True
        assert validate_format_spec("currency:EUR") is True
        assert validate_format_spec("currency:INVALID") is False
        assert validate_format_spec("currency:US") is False

    def test_validate_decimal_format(self):
        """Test decimal format validation."""
        assert validate_format_spec("decimal:2") is True
        assert validate_format_spec("decimal:0") is True
        assert validate_format_spec("decimal:10") is True
        assert validate_format_spec("decimal:-1") is False
        assert validate_format_spec("decimal:abc") is False

    def test_validate_other_formats(self):
        """Test other format validations."""
        assert validate_format_spec("percent") is True
        assert validate_format_spec("integer") is True
        assert validate_format_spec("accounting") is True
        assert validate_format_spec("invalid") is False

    def test_validate_empty_format(self):
        """Test empty format is valid."""
        assert validate_format_spec("") is True
        assert validate_format_spec(None) is True


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_very_large_number(self):
        """Test formatting very large number."""
        result = format_number(1234567890.12, "currency:USD")
        assert "$1,234,567,890.12" in result

    def test_very_small_number(self):
        """Test formatting very small number."""
        result = format_number(0.00001, "decimal:5")
        assert "0.00001" in result

    def test_zero(self):
        """Test formatting zero."""
        result = format_number(0, "currency:USD")
        assert "$0.00" in result

    def test_case_insensitive_format(self):
        """Test format specs are case-insensitive."""
        result1 = format_number(100, "CURRENCY:USD")
        result2 = format_number(100, "currency:usd")
        assert "$100.00" in result1
        assert "$100.00" in result2
