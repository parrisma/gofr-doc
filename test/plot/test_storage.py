"""Tests for PlotStorageWrapper -- metadata segregation and alias support."""

import tempfile

import pytest

from app.storage.common_adapter import CommonStorageAdapter
from app.plot.storage import PlotStorageWrapper


@pytest.fixture
def storage_dir():
    """Create a temporary directory for storage tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def common_adapter(storage_dir):
    """Create a fresh CommonStorageAdapter."""
    return CommonStorageAdapter(storage_dir)


@pytest.fixture
def plot_storage(common_adapter):
    """Create a PlotStorageWrapper around the common adapter."""
    return PlotStorageWrapper(storage=common_adapter)


class TestPlotStorageSave:
    """Save and retrieve plot images."""

    def test_save_returns_guid(self, plot_storage):
        guid = plot_storage.save_image(
            image_data=b"\x89PNG fake image data",
            format="png",
            group="test_group",
        )
        assert isinstance(guid, str)
        assert len(guid) > 0

    def test_save_and_retrieve(self, plot_storage):
        data = b"\x89PNG test image bytes"
        guid = plot_storage.save_image(
            image_data=data,
            format="png",
            group="test_group",
        )
        result = plot_storage.get_image(guid, group="test_group")
        assert result is not None
        image_data, fmt = result
        assert image_data == data
        assert fmt == "png"

    def test_save_with_alias(self, plot_storage):
        _guid = plot_storage.save_image(  # noqa: F841 - GUID not needed, testing alias retrieval
            image_data=b"img data",
            format="png",
            group="test_group",
            alias="my-chart",
        )
        # Should be retrievable by alias
        result = plot_storage.get_image("my-chart", group="test_group")
        assert result is not None

    def test_save_jpg_format(self, plot_storage):
        guid = plot_storage.save_image(
            image_data=b"\xff\xd8 jpeg data",
            format="jpg",
            group="test_group",
        )
        result = plot_storage.get_image(guid, group="test_group")
        assert result is not None
        _, fmt = result
        assert fmt == "jpg"


class TestPlotStorageListImages:
    """List images with metadata segregation."""

    def test_list_empty(self, plot_storage):
        images = plot_storage.list_images(group="test_group")
        assert images == []

    def test_list_after_save(self, plot_storage):
        plot_storage.save_image(
            image_data=b"img1",
            format="png",
            group="test_group",
        )
        plot_storage.save_image(
            image_data=b"img2",
            format="jpg",
            group="test_group",
        )
        images = plot_storage.list_images(group="test_group")
        assert len(images) == 2

    def test_list_filtered_by_group(self, plot_storage):
        plot_storage.save_image(
            image_data=b"img1",
            format="png",
            group="group_a",
        )
        plot_storage.save_image(
            image_data=b"img2",
            format="png",
            group="group_b",
        )
        images_a = plot_storage.list_images(group="group_a")
        images_b = plot_storage.list_images(group="group_b")
        assert len(images_a) == 1
        assert len(images_b) == 1

    def test_list_image_has_expected_fields(self, plot_storage):
        plot_storage.save_image(
            image_data=b"img",
            format="png",
            group="test_group",
            alias="chart1",
        )
        images = plot_storage.list_images(group="test_group")
        assert len(images) == 1
        img = images[0]
        assert "guid" in img
        assert "format" in img
        assert img["format"] == "png"


class TestPlotStorageSegregation:
    """Plot images are segregated from documents via artifact_type."""

    def test_document_not_in_plot_list(self, common_adapter, plot_storage):
        # Save a regular document (not a plot)
        doc_guid = common_adapter.save_document(
            document_data=b"<html>doc</html>",
            format="html",
            group="test_group",
        )
        # Save a plot image
        plot_guid = plot_storage.save_image(
            image_data=b"plot data",
            format="png",
            group="test_group",
        )
        # list_images should only return the plot, not the document
        images = plot_storage.list_images(group="test_group")
        guids = [img["guid"] for img in images]
        assert plot_guid in guids
        assert doc_guid not in guids

    def test_list_image_guids(self, plot_storage):
        guid1 = plot_storage.save_image(
            image_data=b"a",
            format="png",
            group="test_group",
        )
        guid2 = plot_storage.save_image(
            image_data=b"b",
            format="png",
            group="test_group",
        )
        guids = plot_storage.list_image_guids(group="test_group")
        assert guid1 in guids
        assert guid2 in guids


class TestPlotStorageDataUri:
    """Data URI generation for embedding."""

    def test_data_uri_format(self, plot_storage):
        plot_storage.save_image(
            image_data=b"fake png data",
            format="png",
            group="test_group",
            alias="embed-test",
        )
        uri = plot_storage.get_image_as_data_uri("embed-test", group="test_group")
        assert uri is not None
        assert uri.startswith("data:image/png;base64,")

    def test_data_uri_none_for_missing(self, plot_storage):
        uri = plot_storage.get_image_as_data_uri("nonexistent", group="test_group")
        assert uri is None


class TestPlotStorageResolveIdentifier:
    """Identifier resolution (alias and GUID)."""

    def test_resolve_guid(self, plot_storage):
        guid = plot_storage.save_image(
            image_data=b"resolve test",
            format="png",
            group="test_group",
        )
        resolved = plot_storage.resolve_identifier(guid, group="test_group")
        assert resolved == guid

    def test_resolve_alias(self, plot_storage):
        guid = plot_storage.save_image(
            image_data=b"alias resolve",
            format="png",
            group="test_group",
            alias="resolve-me",
        )
        resolved = plot_storage.resolve_identifier("resolve-me", group="test_group")
        assert resolved == guid

    def test_resolve_missing_returns_none(self, plot_storage):
        resolved = plot_storage.resolve_identifier("does-not-exist", group="test_group")
        assert resolved is None


class TestPlotStorageGetAlias:
    """Get alias for a GUID."""

    def test_get_alias(self, plot_storage):
        guid = plot_storage.save_image(
            image_data=b"aliased",
            format="png",
            group="test_group",
            alias="my-alias",
        )
        alias = plot_storage.get_alias(guid)
        assert alias == "my-alias"

    def test_get_alias_none_when_unset(self, plot_storage):
        guid = plot_storage.save_image(
            image_data=b"no alias",
            format="png",
            group="test_group",
        )
        alias = plot_storage.get_alias(guid)
        assert alias is None
