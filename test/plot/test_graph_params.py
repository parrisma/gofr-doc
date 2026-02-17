"""Tests for GraphParams model -- validation, defaults, backward compatibility."""

import pytest

from app.plot.graph_params import GraphParams


class TestGraphParamsBasic:
    """Basic GraphParams construction and defaults."""

    def test_minimal_params(self):
        params = GraphParams(title="Test", y1=[1, 2, 3])
        assert params.title == "Test"
        assert params.y1 == [1, 2, 3]
        assert params.type == "line"
        assert params.format == "png"
        assert params.theme == "light"

    def test_default_axis_labels(self):
        params = GraphParams(title="Test", y1=[1, 2, 3])
        assert params.xlabel == "X-axis"
        assert params.ylabel == "Y-axis"

    def test_default_line_width(self):
        params = GraphParams(title="Test", y1=[1])
        assert params.line_width == 2.0

    def test_default_marker_size(self):
        params = GraphParams(title="Test", y1=[1])
        assert params.marker_size == 36.0

    def test_default_alpha(self):
        params = GraphParams(title="Test", y1=[1])
        assert params.alpha == 1.0

    def test_proxy_defaults_false(self):
        params = GraphParams(title="Test", y1=[1])
        assert params.proxy is False

    def test_return_base64_defaults_true(self):
        params = GraphParams(title="Test", y1=[1])
        assert params.return_base64 is True


class TestGraphParamsBackwardCompat:
    """Backward compatibility: y -> y1, color -> color1."""

    def test_y_maps_to_y1(self):
        params = GraphParams(title="Test", y=[10, 20, 30])
        assert params.y1 == [10, 20, 30]

    def test_y_does_not_override_y1(self):
        params = GraphParams(title="Test", y1=[1, 2], y=[10, 20])
        assert params.y1 == [1, 2]

    def test_color_maps_to_color1(self):
        params = GraphParams(title="Test", y1=[1], color="red")
        assert params.color1 == "red"

    def test_color_does_not_override_color1(self):
        params = GraphParams(title="Test", y1=[1], color1="blue", color="red")
        assert params.color1 == "blue"

    def test_no_y_or_y1_raises(self):
        with pytest.raises(ValueError, match="At least one dataset"):
            GraphParams(title="Test")


class TestGraphParamsMultiDataset:
    """Multi-dataset support (y1-y5)."""

    def test_single_dataset(self):
        params = GraphParams(title="Test", y1=[1, 2, 3])
        datasets = params.get_datasets()
        assert len(datasets) == 1
        assert datasets[0][0] == [1, 2, 3]

    def test_two_datasets(self):
        params = GraphParams(title="Test", y1=[1, 2], y2=[3, 4])
        datasets = params.get_datasets()
        assert len(datasets) == 2

    def test_five_datasets(self):
        params = GraphParams(
            title="Test",
            y1=[1],
            y2=[2],
            y3=[3],
            y4=[4],
            y5=[5],
        )
        datasets = params.get_datasets()
        assert len(datasets) == 5

    def test_labels_in_datasets(self):
        params = GraphParams(
            title="Test",
            y1=[1, 2],
            label1="First",
            y2=[3, 4],
            label2="Second",
        )
        datasets = params.get_datasets()
        assert datasets[0][1] == "First"
        assert datasets[1][1] == "Second"

    def test_colors_in_datasets(self):
        params = GraphParams(
            title="Test",
            y1=[1],
            color1="red",
            y2=[2],
            color2="blue",
        )
        datasets = params.get_datasets()
        assert datasets[0][2] == "red"
        assert datasets[1][2] == "blue"


class TestGraphParamsXValues:
    """X-axis value handling."""

    def test_auto_x_values(self):
        params = GraphParams(title="Test", y1=[10, 20, 30])
        x = params.get_x_values(3)
        assert x == [0, 1, 2]

    def test_explicit_x_values(self):
        params = GraphParams(title="Test", y1=[10, 20], x=[5.0, 10.0])
        x = params.get_x_values(2)
        assert x == [5.0, 10.0]


class TestGraphParamsAxisLimits:
    """Axis limit parameters."""

    def test_axis_limits_default_none(self):
        params = GraphParams(title="Test", y1=[1])
        assert params.xmin is None
        assert params.xmax is None
        assert params.ymin is None
        assert params.ymax is None

    def test_axis_limits_set(self):
        params = GraphParams(
            title="Test",
            y1=[1],
            xmin=0,
            xmax=100,
            ymin=-10,
            ymax=50,
        )
        assert params.xmin == 0
        assert params.xmax == 100
        assert params.ymin == -10
        assert params.ymax == 50


class TestGraphParamsTicks:
    """Tick configuration."""

    def test_ticks_default_none(self):
        params = GraphParams(title="Test", y1=[1])
        assert params.x_major_ticks is None
        assert params.y_major_ticks is None
        assert params.x_minor_ticks is None
        assert params.y_minor_ticks is None

    def test_ticks_set(self):
        params = GraphParams(
            title="Test",
            y1=[1],
            x_major_ticks=[0, 5, 10],
            y_major_ticks=[0, 25, 50],
        )
        assert params.x_major_ticks == [0, 5, 10]
        assert params.y_major_ticks == [0, 25, 50]
