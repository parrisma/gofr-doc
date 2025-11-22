"""Number formatting utilities using Babel.

Provides number formatting for financial data including:
- Currency formatting (USD, EUR, GBP, JPY, etc.)
- Percentage formatting
- Decimal precision formatting
- Integer formatting
- Accounting format (negatives in parentheses)
"""

from typing import Any, Optional
from decimal import Decimal, InvalidOperation

from babel.numbers import format_currency, format_decimal, format_percent


class NumberFormatError(Exception):
    """Raised when number formatting fails."""

    pass


def format_number(value: Any, format_spec: Optional[str] = None, locale: str = "en_US") -> str:
    """Format a number according to the given format specification.

    Args:
        value: The value to format (can be numeric, string, or None)
        format_spec: Format specification string:
            - "currency:USD", "currency:EUR", "currency:GBP", "currency:JPY", etc.
            - "percent" - formats as percentage (0.15 -> 15%)
            - "decimal:N" - formats with N decimal places (e.g., "decimal:2")
            - "integer" - formats as integer (no decimals)
            - "accounting" - formats negatives in parentheses
            - None - returns value as-is
        locale: Locale for formatting (default: "en_US")

    Returns:
        Formatted string representation of the value

    Raises:
        NumberFormatError: If format_spec is invalid or formatting fails
    """
    # Handle None and empty values
    if value is None or value == "":
        return ""

    # If no format specified, return as string
    if format_spec is None or format_spec == "":
        return str(value)

    # Try to convert value to Decimal for formatting
    try:
        if isinstance(value, (int, float)):
            numeric_value = Decimal(str(value))
        elif isinstance(value, str):
            # Try to parse string as number
            numeric_value = Decimal(value.strip().replace(",", ""))
        elif isinstance(value, Decimal):
            numeric_value = value
        else:
            # Non-numeric value, return as-is
            return str(value)
    except (InvalidOperation, ValueError):
        # If conversion fails, return original value
        return str(value)

    # Parse format specification
    format_spec = format_spec.strip().lower()

    try:
        if format_spec.startswith("currency:"):
            # Currency formatting: "currency:USD"
            currency_code = format_spec.split(":", 1)[1].strip().upper()
            if len(currency_code) != 3:
                raise NumberFormatError(f"Invalid currency code: {currency_code}")
            return format_currency(numeric_value, currency_code, locale=locale)

        elif format_spec == "percent":
            # Percentage formatting: multiply by 100 and add %
            return format_percent(numeric_value, locale=locale)

        elif format_spec.startswith("decimal:"):
            # Decimal formatting: "decimal:2" for 2 decimal places
            try:
                decimal_places = int(format_spec.split(":", 1)[1].strip())
                if decimal_places < 0:
                    raise ValueError
                format_pattern = f"#,##0.{'0' * decimal_places}" if decimal_places > 0 else "#,##0"
                return format_decimal(numeric_value, format=format_pattern, locale=locale)
            except (ValueError, IndexError):
                raise NumberFormatError(f"Invalid decimal format: {format_spec}")

        elif format_spec == "integer":
            # Integer formatting: no decimal places
            return format_decimal(numeric_value, format="#,##0", locale=locale)

        elif format_spec == "accounting":
            # Accounting format: negatives in parentheses
            if numeric_value < 0:
                positive_value = abs(numeric_value)
                formatted = format_decimal(positive_value, format="#,##0.00", locale=locale)
                return f"({formatted})"
            else:
                return format_decimal(numeric_value, format="#,##0.00", locale=locale)

        else:
            raise NumberFormatError(f"Unknown format specification: {format_spec}")

    except Exception as e:
        if isinstance(e, NumberFormatError):
            raise
        raise NumberFormatError(
            f"Error formatting value {value} with format {format_spec}: {str(e)}"
        )


def validate_format_spec(format_spec: Optional[str]) -> bool:
    """Validate a format specification string.

    Args:
        format_spec: Format specification to validate

    Returns:
        True if valid, False otherwise
    """
    if not format_spec:
        return True

    format_spec = format_spec.strip().lower()

    # Check currency format
    if format_spec.startswith("currency:"):
        currency_code = format_spec.split(":", 1)[1].strip().upper()
        return len(currency_code) == 3 and currency_code.isalpha()

    # Check decimal format
    if format_spec.startswith("decimal:"):
        try:
            decimal_places = int(format_spec.split(":", 1)[1].strip())
            return decimal_places >= 0
        except (ValueError, IndexError):
            return False

    # Check other formats
    return format_spec in ["percent", "integer", "accounting"]
