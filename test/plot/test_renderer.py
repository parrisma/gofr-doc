"""Tests for GraphRenderer -- headless rendering to base64 and bytes."""

import base64

import pytest

from app.plot.graph_params import GraphParams
from app.plot.render.renderer import GraphRenderer


class TestRendererBasic:
    """Basic rendering tests."""

    def setup_method(self):
        self.renderer = GraphRenderer()

    def test_render_line_base64(self):
        params = GraphParams(title="Line Test", y1=[1, 2, 3, 4, 5])
        result = self.renderer.render(params)
        assert isinstance(result, str)
        # Should be valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_render_scatter_base64(self):
        params = GraphParams(title="Scatter", y1=[10, 20, 30], type="scatter")
        result = self.renderer.render(params)
        assert isinstance(result, str)
        decoded = base64.b64decode(result)
        assert len(decoded) > 100

    def test_render_bar_base64(self):
        params = GraphParams(title="Bar Chart", y1=[5, 10, 15], type="bar")
        result = self.renderer.render(params)
        assert isinstance(result, str)
        decoded = base64.b64decode(result)
        assert len(decoded) > 100


class TestRendererFormats:
    """Output format tests."""

    def setup_method(self):
        self.renderer = GraphRenderer()

    def test_render_png(self):
        params = GraphParams(title="PNG", y1=[1, 2, 3], format="png")
        result = self.renderer.render(params)
        decoded = base64.b64decode(result)
        # PNG magic bytes
        assert decoded[:4] == b"\x89PNG"

    def test_render_jpg(self):
        params = GraphParams(title="JPG", y1=[1, 2, 3], format="jpg")
        result = self.renderer.render(params)
        decoded = base64.b64decode(result)
        # JPEG magic bytes
        assert decoded[:2] == b"\xff\xd8"

    def test_render_svg(self):
        params = GraphParams(title="SVG", y1=[1, 2, 3], format="svg")
        result = self.renderer.render(params)
        decoded = base64.b64decode(result)
        svg_text = decoded.decode("utf-8")
        assert "<svg" in svg_text

    def test_render_pdf(self):
        params = GraphParams(title="PDF", y1=[1, 2, 3], format="pdf")
        result = self.renderer.render(params)
        decoded = base64.b64decode(result)
        assert decoded[:4] == b"%PDF"


class TestRendererToBytes:
    """render_to_bytes helper."""

    def setup_method(self):
        self.renderer = GraphRenderer()

    def test_returns_bytes(self):
        params = GraphParams(title="Bytes", y1=[1, 2, 3])
        result = self.renderer.render_to_bytes(params)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_png_magic_bytes(self):
        params = GraphParams(title="PNG Bytes", y1=[1, 2, 3], format="png")
        result = self.renderer.render_to_bytes(params)
        assert result[:4] == b"\x89PNG"

    def test_does_not_mutate_input(self):
        params = GraphParams(title="Immutable", y1=[1, 2, 3])
        assert params.return_base64 is True
        self.renderer.render_to_bytes(params)
        assert params.return_base64 is True


class TestRendererThemes:
    """Theme application during rendering."""

    def setup_method(self):
        self.renderer = GraphRenderer()

    def test_light_theme_renders(self):
        params = GraphParams(title="Light", y1=[1, 2, 3], theme="light")
        result = self.renderer.render(params)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_dark_theme_renders(self):
        params = GraphParams(title="Dark", y1=[1, 2, 3], theme="dark")
        result = self.renderer.render(params)
        assert isinstance(result, str)

    def test_bizlight_theme_renders(self):
        params = GraphParams(title="BizLight", y1=[1, 2, 3], theme="bizlight")
        result = self.renderer.render(params)
        assert isinstance(result, str)

    def test_bizdark_theme_renders(self):
        params = GraphParams(title="BizDark", y1=[1, 2, 3], theme="bizdark")
        result = self.renderer.render(params)
        assert isinstance(result, str)

    def test_invalid_theme_raises(self):
        params = GraphParams(title="Invalid", y1=[1, 2, 3], theme="invalid_theme")
        with pytest.raises(ValueError):
            self.renderer.render(params)


class TestRendererMultiDataset:
    """Multi-dataset rendering."""

    def setup_method(self):
        self.renderer = GraphRenderer()

    def test_two_datasets(self):
        params = GraphParams(
            title="Two Lines",
            y1=[1, 2, 3],
            y2=[3, 2, 1],
            label1="A",
            label2="B",
        )
        result = self.renderer.render(params)
        assert isinstance(result, str)
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_five_datasets(self):
        params = GraphParams(
            title="Five Lines",
            y1=[1, 2],
            y2=[2, 3],
            y3=[3, 4],
            y4=[4, 5],
            y5=[5, 6],
        )
        result = self.renderer.render(params)
        assert isinstance(result, str)

    def test_multi_dataset_with_colors(self):
        params = GraphParams(
            title="Colored",
            y1=[1, 2, 3],
            color1="red",
            y2=[3, 2, 1],
            color2="blue",
        )
        result = self.renderer.render(params)
        assert isinstance(result, str)


class TestRendererAxisControls:
    """Axis limits and ticks."""

    def setup_method(self):
        self.renderer = GraphRenderer()

    def test_axis_limits(self):
        params = GraphParams(
            title="Limits",
            y1=[1, 2, 3],
            xmin=0,
            xmax=5,
            ymin=-1,
            ymax=10,
        )
        result = self.renderer.render(params)
        assert isinstance(result, str)

    def test_major_ticks(self):
        params = GraphParams(
            title="Ticks",
            y1=[1, 2, 3],
            x_major_ticks=[0.0, 1.0, 2.0],
            y_major_ticks=[0.0, 1.5, 3.0],
        )
        result = self.renderer.render(params)
        assert isinstance(result, str)

    def test_minor_ticks(self):
        params = GraphParams(
            title="Minor",
            y1=[1, 2, 3],
            x_minor_ticks=[0.5, 1.5],
        )
        result = self.renderer.render(params)
        assert isinstance(result, str)


class TestRendererCustomStyle:
    """Custom line width, marker size, alpha."""

    def setup_method(self):
        self.renderer = GraphRenderer()

    def test_custom_line_width(self):
        params = GraphParams(title="Wide", y1=[1, 2, 3], line_width=5.0)
        result = self.renderer.render(params)
        assert isinstance(result, str)

    def test_custom_marker_size(self):
        params = GraphParams(
            title="Big Markers",
            y1=[1, 2, 3],
            type="scatter",
            marker_size=100.0,
        )
        result = self.renderer.render(params)
        assert isinstance(result, str)

    def test_custom_alpha(self):
        params = GraphParams(title="Transparent", y1=[1, 2, 3], alpha=0.5)
        result = self.renderer.render(params)
        assert isinstance(result, str)
