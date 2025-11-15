"""Tests for handler descriptions and handler listing functionality"""

import pytest
from app.handlers import (
    list_handlers_with_descriptions,
    LineGraphHandler,
    ScatterGraphHandler,
    BarGraphHandler,
)


def test_all_handlers_have_descriptions():
    """Test that all handlers have descriptions"""
    handlers = [
        ("line", LineGraphHandler()),
        ("scatter", ScatterGraphHandler()),
        ("bar", BarGraphHandler()),
    ]

    for handler_name, handler in handlers:
        description = handler.get_description()

        assert description is not None, f"Handler {handler_name} has no description"
        assert len(description) > 0, f"Handler {handler_name} has empty description"
        assert isinstance(description, str), f"Handler {handler_name} description is not a string"


def test_line_handler_description():
    """Test that line handler has appropriate description"""
    handler = LineGraphHandler()
    description = handler.get_description()

    assert "line" in description.lower() or "trend" in description.lower()
    assert len(description) > 20  # Should be descriptive enough


def test_scatter_handler_description():
    """Test that scatter handler has appropriate description"""
    handler = ScatterGraphHandler()
    description = handler.get_description()

    assert "scatter" in description.lower() or "relationship" in description.lower()
    assert len(description) > 20


def test_bar_handler_description():
    """Test that bar handler has appropriate description"""
    handler = BarGraphHandler()
    description = handler.get_description()

    assert "bar" in description.lower() or "categor" in description.lower()
    assert len(description) > 20


def test_list_handlers_with_descriptions():
    """Test that list_handlers_with_descriptions returns all handlers"""
    handlers_dict = list_handlers_with_descriptions()

    # Check that we have all expected handlers
    expected_handlers = {"line", "scatter", "bar"}
    assert set(handlers_dict.keys()) == expected_handlers

    # Check that all descriptions are non-empty strings
    for handler_name, description in handlers_dict.items():
        assert isinstance(description, str)
        assert len(description) > 0


def test_list_handlers_with_descriptions_format():
    """Test that descriptions are properly formatted"""
    handlers_dict = list_handlers_with_descriptions()

    for handler_name, description in handlers_dict.items():
        # Description should not have trailing whitespace
        assert description == description.strip()

        # Description should start with a capital letter or lowercase for type names
        assert description[0].isupper() or description.split()[0] in ["line", "scatter", "bar"]

        # Description should be at least 20 characters
        assert len(description) >= 20


def test_handlers_with_descriptions_are_unique():
    """Test that each handler has a unique description"""
    handlers_dict = list_handlers_with_descriptions()
    descriptions = list(handlers_dict.values())

    # All descriptions should be unique
    assert len(descriptions) == len(set(descriptions))


def test_descriptions_mention_multiple_datasets():
    """Test that all handler descriptions mention multiple dataset support"""
    handlers_dict = list_handlers_with_descriptions()

    for handler_name, description in handlers_dict.items():
        assert (
            "multiple" in description.lower()
        ), f"Handler {handler_name} description should mention multiple dataset support"
