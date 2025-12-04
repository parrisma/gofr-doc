#!/usr/bin/env python3
"""Test storage purge functionality"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from app.storage.file_storage import FileStorage
from app.logger import Logger, session_logger


@pytest.fixture
def temp_storage_dir():
    """Create a temporary storage directory for tests"""
    temp_dir = tempfile.mkdtemp(prefix="gofr_doc_purge_test_")
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def storage_with_images(temp_storage_dir):
    """Create storage with test images"""
    logger: Logger = session_logger
    storage = FileStorage(storage_dir=temp_storage_dir)

    # Create images in different groups
    guids = {"group1": [], "group2": [], "no_group": []}

    # Add 3 images to group1
    for i in range(3):
        guid = storage.save_image(f"group1_image_{i}".encode(), format="png", group="group1")
        guids["group1"].append(guid)

    # Add 2 images to group2
    for i in range(2):
        guid = storage.save_image(f"group2_image_{i}".encode(), format="png", group="group2")
        guids["group2"].append(guid)

    # Add 2 images with no group
    for i in range(2):
        guid = storage.save_image(f"no_group_image_{i}".encode(), format="png", group=None)
        guids["no_group"].append(guid)

    logger.info(
        "Created test images",
        group1=len(guids["group1"]),
        group2=len(guids["group2"]),
        no_group=len(guids["no_group"]),
    )

    return storage, guids


def test_purge_all_images(storage_with_images):
    """Test purging all images (age_days=0, no group filter)"""
    logger: Logger = session_logger
    logger.info("Testing purge all images")

    storage, guids = storage_with_images

    # Verify initial count
    initial_count = len(storage.list_images())
    assert initial_count == 7, f"Expected 7 images, found {initial_count}"

    # Purge all images
    deleted = storage.purge(age_days=0)

    # Verify all deleted
    assert deleted == 7, f"Expected 7 deleted, got {deleted}"
    assert len(storage.list_images()) == 0, "Storage should be empty"
    logger.info("Successfully purged all images", deleted=deleted)


def test_purge_specific_group(storage_with_images):
    """Test purging images from a specific group only"""
    logger: Logger = session_logger
    logger.info("Testing purge specific group")

    storage, guids = storage_with_images

    # Purge only group1 images
    deleted = storage.purge(age_days=0, group="group1")

    # Verify only group1 deleted
    assert deleted == 3, f"Expected 3 deleted from group1, got {deleted}"

    remaining = storage.list_images()
    assert len(remaining) == 4, f"Expected 4 remaining, got {len(remaining)}"

    # Verify group1 images are gone
    for guid in guids["group1"]:
        assert not storage.exists(guid), f"group1 image {guid} should be deleted"

    # Verify other images still exist
    for guid in guids["group2"] + guids["no_group"]:
        assert storage.exists(guid), f"Image {guid} should still exist"

    logger.info("Successfully purged only group1 images", deleted=deleted, remaining=len(remaining))


def test_purge_by_age_no_old_images(storage_with_images):
    """Test purging by age when no images are old enough"""
    logger: Logger = session_logger
    logger.info("Testing purge by age with no old images")

    storage, guids = storage_with_images

    # Try to purge images older than 30 days (all images are brand new)
    deleted = storage.purge(age_days=30)

    # Nothing should be deleted
    assert deleted == 0, f"Expected 0 deleted, got {deleted}"
    assert len(storage.list_images()) == 7, "All images should remain"

    logger.info("Correctly preserved recent images", deleted=deleted)


def test_purge_by_age_with_old_images(temp_storage_dir):
    """Test purging by age with artificially aged images"""
    logger: Logger = session_logger
    logger.info("Testing purge by age with old images")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Create some images
    guid_new = storage.save_image(b"new_image", format="png", group="test")
    guid_old = storage.save_image(b"old_image", format="png", group="test")

    # Artificially age one image by modifying its metadata timestamp
    old_date = (datetime.utcnow() - timedelta(days=31)).isoformat()
    storage.metadata[guid_old]["created_at"] = old_date
    storage._save_metadata()

    logger.info("Created images", new=guid_new, old=guid_old, old_date=old_date)

    # Purge images older than 30 days
    deleted = storage.purge(age_days=30, group="test")

    # Only the old image should be deleted
    assert deleted == 1, f"Expected 1 deleted, got {deleted}"
    assert storage.exists(guid_new), "New image should still exist"
    assert not storage.exists(guid_old), "Old image should be deleted"

    logger.info("Successfully purged only old images", deleted=deleted)


def test_purge_with_group_filter_and_age(temp_storage_dir):
    """Test purging with both group filter and age criteria"""
    logger: Logger = session_logger
    logger.info("Testing purge with group filter and age")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Create images in different groups with different ages
    guid_g1_old = storage.save_image(b"group1_old", format="png", group="group1")
    guid_g1_new = storage.save_image(b"group1_new", format="png", group="group1")
    guid_g2_old = storage.save_image(b"group2_old", format="png", group="group2")

    # Age some images
    old_date = (datetime.utcnow() - timedelta(days=31)).isoformat()
    storage.metadata[guid_g1_old]["created_at"] = old_date
    storage.metadata[guid_g2_old]["created_at"] = old_date
    storage._save_metadata()

    # Purge only old group1 images
    deleted = storage.purge(age_days=30, group="group1")

    # Only group1 old image should be deleted
    assert deleted == 1, f"Expected 1 deleted, got {deleted}"
    assert not storage.exists(guid_g1_old), "group1 old image should be deleted"
    assert storage.exists(guid_g1_new), "group1 new image should exist"
    assert storage.exists(guid_g2_old), "group2 old image should exist (different group)"

    logger.info("Correctly filtered by both group and age", deleted=deleted)


def test_purge_empty_storage(temp_storage_dir):
    """Test purging when storage is already empty"""
    logger: Logger = session_logger
    logger.info("Testing purge on empty storage")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Purge empty storage
    deleted = storage.purge(age_days=0)

    assert deleted == 0, f"Expected 0 deleted from empty storage, got {deleted}"
    logger.info("Handled empty storage correctly", deleted=deleted)


def test_purge_with_missing_metadata(temp_storage_dir):
    """Test purging images that have files but missing metadata"""
    logger: Logger = session_logger
    logger.info("Testing purge with missing metadata")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Create an image
    guid = storage.save_image(b"test_image", format="png", group="test")

    # Remove metadata entry (simulate corrupted metadata)
    del storage.metadata[guid]
    storage._save_metadata()

    # Purge should handle missing metadata gracefully (uses file mtime)
    deleted = storage.purge(age_days=0)

    assert deleted == 1, f"Expected 1 deleted, got {deleted}"
    logger.info("Handled missing metadata by falling back to file mtime", deleted=deleted)


def test_purge_preserves_metadata_consistency(storage_with_images):
    """Test that purge maintains metadata consistency"""
    logger: Logger = session_logger
    logger.info("Testing metadata consistency after purge")

    storage, guids = storage_with_images

    # Get initial metadata keys
    initial_metadata_keys = set(storage.metadata.keys())

    # Purge group1
    deleted = storage.purge(age_days=0, group="group1")

    # Verify metadata was updated
    remaining_metadata_keys = set(storage.metadata.keys())

    # group1 GUIDs should be removed from metadata
    for guid in guids["group1"]:
        assert guid not in remaining_metadata_keys, f"Metadata for {guid} should be removed"

    # Other GUIDs should remain
    for guid in guids["group2"] + guids["no_group"]:
        assert guid in remaining_metadata_keys, f"Metadata for {guid} should remain"

    logger.info(
        "Metadata consistency maintained",
        initial=len(initial_metadata_keys),
        remaining=len(remaining_metadata_keys),
        deleted=deleted,
    )


def test_purge_return_value(storage_with_images):
    """Test that purge returns correct count of deleted images"""
    logger: Logger = session_logger
    logger.info("Testing purge return value accuracy")

    storage, guids = storage_with_images

    # Test different purge scenarios and verify counts

    # Scenario 1: Purge group with 3 images
    deleted = storage.purge(age_days=0, group="group1")
    assert deleted == 3, f"Expected 3, got {deleted}"

    # Scenario 2: Purge group with 2 images
    deleted = storage.purge(age_days=0, group="group2")
    assert deleted == 2, f"Expected 2, got {deleted}"

    # Scenario 3: Purge remaining (2 no_group images)
    deleted = storage.purge(age_days=0)
    assert deleted == 2, f"Expected 2, got {deleted}"

    logger.info("Purge return values are accurate")


def test_purge_with_invalid_metadata_timestamps(temp_storage_dir):
    """Test purging with corrupted timestamp data in metadata"""
    logger: Logger = session_logger
    logger.info("Testing purge with invalid metadata timestamps")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Create an image
    guid = storage.save_image(b"test_image", format="png", group="test")

    # Corrupt the timestamp
    storage.metadata[guid]["created_at"] = "invalid_date_format"
    storage._save_metadata()

    # Purge should fall back to file modification time
    deleted = storage.purge(age_days=0)

    assert deleted == 1, f"Expected 1 deleted despite invalid timestamp, got {deleted}"
    logger.info("Handled invalid timestamp by falling back to file mtime", deleted=deleted)


def test_purge_multiple_times(storage_with_images):
    """Test running purge multiple times"""
    logger: Logger = session_logger
    logger.info("Testing multiple purge operations")

    storage, guids = storage_with_images

    # First purge - remove group1
    deleted1 = storage.purge(age_days=0, group="group1")
    assert deleted1 == 3

    # Second purge - same group (should find nothing)
    deleted2 = storage.purge(age_days=0, group="group1")
    assert deleted2 == 0, "Second purge should find no images to delete"

    # Third purge - remove everything
    deleted3 = storage.purge(age_days=0)
    assert deleted3 == 4, "Should delete remaining 4 images"

    # Fourth purge - empty storage
    deleted4 = storage.purge(age_days=0)
    assert deleted4 == 0, "Fourth purge on empty storage should delete nothing"

    logger.info(
        "Multiple purge operations handled correctly",
        purge1=deleted1,
        purge2=deleted2,
        purge3=deleted3,
        purge4=deleted4,
    )


def test_purge_does_not_delete_metadata_file(storage_with_images):
    """Test that purge never deletes the metadata.json file"""
    logger: Logger = session_logger
    logger.info("Testing that metadata.json is preserved")

    storage, guids = storage_with_images

    metadata_file = storage.storage_dir / "metadata.json"
    assert metadata_file.exists(), "Metadata file should exist initially"

    # Purge everything
    storage.purge(age_days=0)

    # Metadata file should still exist
    assert metadata_file.exists(), "Metadata file should not be deleted by purge"
    logger.info("Metadata file preserved after purge")


def test_purge_with_different_image_formats(temp_storage_dir):
    """Test purging images with different formats"""
    logger: Logger = session_logger
    logger.info("Testing purge with different image formats")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Create images with different formats
    guid_png = storage.save_image(b"png_data", format="png", group="test")
    guid_jpg = storage.save_image(b"jpg_data", format="jpg", group="test")
    guid_svg = storage.save_image(b"svg_data", format="svg", group="test")

    # Purge all
    deleted = storage.purge(age_days=0, group="test")

    # All should be deleted regardless of format
    assert deleted == 3, f"Expected 3 deleted, got {deleted}"
    assert not storage.exists(guid_png), "PNG should be deleted"
    assert not storage.exists(guid_jpg), "JPG should be deleted"
    assert not storage.exists(guid_svg), "SVG should be deleted"

    logger.info("All image formats purged correctly", deleted=deleted)


def test_purge_cleans_orphaned_metadata(temp_storage_dir):
    """Test that purge removes orphaned metadata entries (entries without files)"""
    logger: Logger = session_logger
    logger.info("Testing purge cleans orphaned metadata")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Create images
    guid1 = storage.save_image(b"image1", format="png", group="test")
    guid2 = storage.save_image(b"image2", format="png", group="test")

    # Verify initial state
    assert len(storage.metadata) == 2, "Should have 2 metadata entries"
    assert len(storage.list_images()) == 2, "Should have 2 image files"

    # Manually delete the files but leave metadata (simulates orphaned metadata)
    (storage.storage_dir / f"{guid1}.png").unlink()
    (storage.storage_dir / f"{guid2}.png").unlink()

    # Verify orphaned state
    assert len(storage.metadata) == 2, "Metadata should still have 2 entries"
    assert len(storage.list_images()) == 0, "No files should exist"

    # Run purge - should clean up orphaned metadata
    deleted = storage.purge(age_days=0)

    # Should report 2 deletions (2 orphaned metadata entries)
    assert deleted == 2, f"Expected 2 deleted (2 orphaned metadata), got {deleted}"
    assert len(storage.metadata) == 0, "All metadata should be cleaned up"
    assert len(storage.list_images()) == 0, "No files should remain"

    logger.info("Orphaned metadata successfully cleaned up", deleted=deleted)


def test_purge_cleans_orphaned_metadata_with_group_filter(temp_storage_dir):
    """Test that purge cleans orphaned metadata only for specified group"""
    logger: Logger = session_logger
    logger.info("Testing purge cleans orphaned metadata with group filter")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Create images in different groups
    guid_g1 = storage.save_image(b"group1", format="png", group="group1")
    guid_g2 = storage.save_image(b"group2", format="png", group="group2")

    # Manually delete only group1 file
    (storage.storage_dir / f"{guid_g1}.png").unlink()

    # Verify orphaned state
    assert len(storage.metadata) == 2, "Should have 2 metadata entries"
    assert len(storage.list_images()) == 1, "Should have 1 file"

    # Purge only group1
    deleted = storage.purge(age_days=0, group="group1")

    # Should clean up only group1 orphaned metadata
    assert deleted == 1, f"Expected 1 deleted (group1 orphaned), got {deleted}"
    assert len(storage.metadata) == 1, "group2 metadata should remain"
    assert guid_g2 in storage.metadata, "group2 metadata should remain"
    assert guid_g1 not in storage.metadata, "group1 metadata should be removed"

    logger.info("Group-filtered orphaned metadata cleanup successful", deleted=deleted)


def test_purge_cleans_orphaned_metadata_with_age_filter(temp_storage_dir):
    """Test that purge cleans orphaned metadata respecting age filter"""
    logger: Logger = session_logger
    logger.info("Testing purge cleans orphaned metadata with age filter")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Create images
    guid_old = storage.save_image(b"old_image", format="png", group="test")
    guid_new = storage.save_image(b"new_image", format="png", group="test")

    # Age the old image
    old_date = (datetime.utcnow() - timedelta(days=31)).isoformat()
    storage.metadata[guid_old]["created_at"] = old_date
    storage._save_metadata()

    # Manually delete both files (create orphaned metadata)
    (storage.storage_dir / f"{guid_old}.png").unlink()
    (storage.storage_dir / f"{guid_new}.png").unlink()

    # Verify orphaned state
    assert len(storage.metadata) == 2, "Should have 2 orphaned metadata entries"
    assert len(storage.list_images()) == 0, "No files should exist"

    # Purge with age filter
    deleted = storage.purge(age_days=30, group="test")

    # Should clean up only old orphaned metadata
    assert deleted == 1, f"Expected 1 deleted (old orphaned), got {deleted}"
    assert len(storage.metadata) == 1, "New metadata should remain"
    assert guid_new in storage.metadata, "New metadata should remain"
    assert guid_old not in storage.metadata, "Old metadata should be removed"

    logger.info("Age-filtered orphaned metadata cleanup successful", deleted=deleted)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
