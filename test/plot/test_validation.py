"""Tests for GraphDataValidator -- structured validation with error messages."""

from app.plot.graph_params import GraphParams
from app.plot.validation.validator import GraphDataValidator


class TestValidatorBasic:
    """Basic validation cases."""

    def setup_method(self):
        self.validator = GraphDataValidator()

    def test_valid_simple_graph(self):
        params = GraphParams(title="Test", y1=[1, 2, 3])
        result = self.validator.validate(params)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_valid_multi_dataset(self):
        params = GraphParams(
            title="Test",
            y1=[1, 2, 3],
            y2=[4, 5, 6],
            y3=[7, 8, 9],
        )
        result = self.validator.validate(params)
        assert result.is_valid is True

    def test_valid_with_x(self):
        params = GraphParams(title="Test", y1=[1, 2, 3], x=[10.0, 20.0, 30.0])
        result = self.validator.validate(params)
        assert result.is_valid is True


class TestValidatorArrayErrors:
    """Array validation errors."""

    def setup_method(self):
        self.validator = GraphDataValidator()

    def test_mismatched_dataset_lengths(self):
        params = GraphParams(title="Test", y1=[1, 2, 3], y2=[4, 5])
        result = self.validator.validate(params)
        assert result.is_valid is False
        error_fields = [e.field for e in result.errors]
        assert "y2" in error_fields

    def test_mismatched_x_length(self):
        params = GraphParams(title="Test", y1=[1, 2, 3], x=[1.0, 2.0])
        result = self.validator.validate(params)
        assert result.is_valid is False
        error_fields = [e.field for e in result.errors]
        assert "x" in error_fields


class TestValidatorTypeErrors:
    """Chart type validation."""

    def setup_method(self):
        self.validator = GraphDataValidator()

    def test_invalid_type(self):
        params = GraphParams(title="Test", y1=[1], type="pie")
        result = self.validator.validate(params)
        assert result.is_valid is False
        error_fields = [e.field for e in result.errors]
        assert "type" in error_fields

    def test_valid_types(self):
        for chart_type in ("line", "scatter", "bar"):
            params = GraphParams(title="Test", y1=[1, 2], type=chart_type)
            result = self.validator.validate(params)
            assert result.is_valid is True, f"Type '{chart_type}' should be valid"


class TestValidatorFormatErrors:
    """Format validation."""

    def setup_method(self):
        self.validator = GraphDataValidator()

    def test_invalid_format(self):
        params = GraphParams(title="Test", y1=[1], format="bmp")
        result = self.validator.validate(params)
        assert result.is_valid is False
        error_fields = [e.field for e in result.errors]
        assert "format" in error_fields

    def test_valid_formats(self):
        for fmt in ("png", "jpg", "svg", "pdf"):
            params = GraphParams(title="Test", y1=[1, 2], format=fmt)
            result = self.validator.validate(params)
            assert result.is_valid is True, f"Format '{fmt}' should be valid"


class TestValidatorThemeErrors:
    """Theme validation."""

    def setup_method(self):
        self.validator = GraphDataValidator()

    def test_invalid_theme(self):
        params = GraphParams(title="Test", y1=[1], theme="neon")
        result = self.validator.validate(params)
        assert result.is_valid is False
        error_fields = [e.field for e in result.errors]
        assert "theme" in error_fields

    def test_valid_themes(self):
        for theme in ("light", "dark", "bizlight", "bizdark"):
            params = GraphParams(title="Test", y1=[1, 2], theme=theme)
            result = self.validator.validate(params)
            assert result.is_valid is True, f"Theme '{theme}' should be valid"


class TestValidatorErrorStructure:
    """Validation error structure quality."""

    def setup_method(self):
        self.validator = GraphDataValidator()

    def test_error_has_field(self):
        params = GraphParams(title="Test", y1=[1], type="pie")
        result = self.validator.validate(params)
        assert len(result.errors) > 0
        error = result.errors[0]
        assert error.field == "type"

    def test_error_has_message(self):
        params = GraphParams(title="Test", y1=[1], type="pie")
        result = self.validator.validate(params)
        error = result.errors[0]
        assert len(error.message) > 0

    def test_error_to_dict(self):
        params = GraphParams(title="Test", y1=[1], type="pie")
        result = self.validator.validate(params)
        error_dict = result.errors[0].to_dict()
        assert "field" in error_dict
        assert "message" in error_dict
        assert "suggestions" in error_dict

    def test_error_suggestions_are_list(self):
        params = GraphParams(title="Test", y1=[1], type="pie")
        result = self.validator.validate(params)
        error_dict = result.errors[0].to_dict()
        assert isinstance(error_dict["suggestions"], list)
