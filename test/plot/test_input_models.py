"""Tests for plot validation input models (Pydantic)."""

import pytest
from pydantic import ValidationError

from app.validation.plot_models import (
    AddPlotFragmentInput,
    GetImageInput,
    ListImagesInput,
    RenderGraphInput,
)


class TestRenderGraphInput:
    """RenderGraphInput model validation."""

    def test_minimal(self):
        m = RenderGraphInput(title="Test")
        assert m.title == "Test"
        assert m.type == "line"
        assert m.format == "png"
        assert m.theme == "light"
        assert m.proxy is False

    def test_with_data(self):
        m = RenderGraphInput(title="Test", y1=[1.0, 2.0, 3.0])
        assert m.y1 == [1.0, 2.0, 3.0]

    def test_missing_title_raises(self):
        with pytest.raises(ValidationError):
            RenderGraphInput()  # pyright: ignore[reportCallIssue]

    def test_extra_fields_ignored(self):
        m = RenderGraphInput(title="Test", unknown_field="val")  # pyright: ignore[reportCallIssue]
        assert not hasattr(m, "unknown_field")

    def test_auth_token_field(self):
        m = RenderGraphInput(title="Test", auth_token="jwt-token")
        assert m.auth_token == "jwt-token"

    def test_group_default(self):
        m = RenderGraphInput(title="Test")
        assert m.group == "public"


class TestGetImageInput:
    """GetImageInput model validation."""

    def test_minimal(self):
        m = GetImageInput(identifier="some-guid")
        assert m.identifier == "some-guid"
        assert m.group == "public"

    def test_missing_identifier_raises(self):
        with pytest.raises(ValidationError):
            GetImageInput()  # pyright: ignore[reportCallIssue]

    def test_auth_token(self):
        m = GetImageInput(identifier="guid", auth_token="tok")
        assert m.auth_token == "tok"


class TestListImagesInput:
    """ListImagesInput model validation."""

    def test_minimal(self):
        m = ListImagesInput()
        assert m.group == "public"

    def test_auth_token(self):
        m = ListImagesInput(auth_token="tok")
        assert m.auth_token == "tok"


class TestAddPlotFragmentInput:
    """AddPlotFragmentInput model validation."""

    def test_minimal(self):
        m = AddPlotFragmentInput(session_id="sess-123")
        assert m.session_id == "sess-123"
        assert m.plot_guid is None
        assert m.title is None

    def test_guid_mode(self):
        m = AddPlotFragmentInput(session_id="sess", plot_guid="guid-abc")
        assert m.plot_guid == "guid-abc"

    def test_inline_mode(self):
        m = AddPlotFragmentInput(
            session_id="sess",
            title="My Chart",
            y1=[1.0, 2.0, 3.0],
            type="bar",
        )
        assert m.title == "My Chart"
        assert m.y1 == [1.0, 2.0, 3.0]
        assert m.type == "bar"

    def test_missing_session_id_raises(self):
        with pytest.raises(ValidationError):
            AddPlotFragmentInput(title="No Session")  # pyright: ignore[reportCallIssue]

    def test_image_params(self):
        m = AddPlotFragmentInput(
            session_id="sess",
            width=800,
            height=600,
            alt_text="A chart",
            alignment="left",
        )
        assert m.width == 800
        assert m.height == 600
        assert m.alt_text == "A chart"
        assert m.alignment == "left"

    def test_position_default_none(self):
        m = AddPlotFragmentInput(session_id="sess")
        assert m.position is None

    def test_extra_fields_ignored(self):
        m = AddPlotFragmentInput(session_id="sess", bogus="val")  # pyright: ignore[reportCallIssue]
        assert not hasattr(m, "bogus")
