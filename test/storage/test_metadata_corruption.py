#!/usr/bin/env python3
"""Test storage resilience when metadata.json is corrupted"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import os
import json
import tempfile
import shutil
from app.storage.file_storage import FileStorage
from app.logger import Logger, session_logger


@pytest.fixture
def temp_storage_dir():
    """Create a temporary storage directory for tests"""
    temp_dir = tempfile.mkdtemp(prefix="gofr_doc_metadata_test_")
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_corrupted_metadata_json(temp_storage_dir):
    """Test recovery when metadata.json contains invalid JSON"""
    logger: Logger = session_logger
    logger.info("Testing corrupted metadata.json recovery")

    # Create metadata file with invalid JSON
    metadata_path = os.path.join(temp_storage_dir, "metadata.json")
    with open(metadata_path, "w") as f:
        f.write("{invalid json here!!!")

    # Initialize storage (should handle corrupted metadata)
    storage = FileStorage(storage_dir=temp_storage_dir)

    # Storage should initialize with empty metadata
    assert storage.metadata == {}, "Metadata should be reset to empty on corruption"

    # Should be able to save new images
    test_data = b"test image after corruption"
    guid = storage.save_image(test_data, format="png", group="test")
    logger.info("Storage recovered from corrupted metadata", guid=guid)

    # Verify metadata was rewritten correctly
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    assert guid in metadata, "New GUID should be in metadata"


def test_missing_metadata_json(temp_storage_dir):
    """Test initialization when metadata.json doesn't exist"""
    logger: Logger = session_logger
    logger.info("Testing missing metadata.json")

    # Initialize storage without metadata file
    storage = FileStorage(storage_dir=temp_storage_dir)

    # Should create new metadata
    test_data = b"test image"
    guid = storage.save_image(test_data, format="png", group="test")

    # Metadata should be created
    metadata_path = os.path.join(temp_storage_dir, "metadata.json")
    assert os.path.exists(metadata_path), "Metadata file should be created"

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    assert guid in metadata, "GUID should be in metadata"
    logger.info("Storage created new metadata successfully")


def test_metadata_with_orphaned_entries(temp_storage_dir):
    """Test when metadata references images that don't exist"""
    logger: Logger = session_logger
    logger.info("Testing metadata with orphaned entries")

    # Create storage and save an image
    storage = FileStorage(storage_dir=temp_storage_dir)
    test_data = b"test image"
    guid = storage.save_image(test_data, format="png", group="test")

    # Delete the image file but keep metadata
    image_path = os.path.join(temp_storage_dir, f"{guid}.png")
    os.remove(image_path)

    # Try to retrieve (should return None)
    result = storage.get_image(guid, group="test")
    assert result is None, "Should return None for missing image"
    logger.info("Storage handled orphaned metadata entry")


def test_images_without_metadata_entries(temp_storage_dir):
    """Test when image files exist but aren't in metadata"""
    logger: Logger = session_logger
    logger.info("Testing orphaned image files without metadata")

    # Create storage
    storage = FileStorage(storage_dir=temp_storage_dir)

    # Manually create an image file without metadata
    orphan_guid = "12345678-1234-1234-1234-123456789abc"
    orphan_path = os.path.join(temp_storage_dir, f"{orphan_guid}.png")
    with open(orphan_path, "wb") as f:
        f.write(b"orphan image data")

    # Trying to retrieve should work (file exists)
    result = storage.get_image(orphan_guid)

    # Should find the image even without metadata
    assert result is not None, "Should find orphaned image file"
    image_data, format_type = result
    assert image_data == b"orphan image data"
    logger.info("Storage found orphaned image file without metadata")


def test_metadata_with_wrong_format(temp_storage_dir):
    """Test when metadata has wrong format but file has correct extension"""
    logger: Logger = session_logger
    logger.info("Testing metadata format mismatch")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Save image
    test_data = b"PNG image data"
    guid = storage.save_image(test_data, format="png", group="test")

    # Manually change metadata format
    storage.metadata[guid]["format"] = "jpg"
    storage._save_metadata()

    # Retrieve should still work (will try multiple formats)
    result = storage.get_image(guid, group="test")
    assert result is not None, "Should find image despite metadata mismatch"
    logger.info("Storage handled format mismatch")


def test_concurrent_metadata_updates(temp_storage_dir):
    """Test that concurrent saves update metadata correctly"""
    logger: Logger = session_logger
    logger.info("Testing concurrent metadata updates")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Save multiple images
    guids = []
    for i in range(5):
        test_data = f"image {i}".encode()
        guid = storage.save_image(test_data, format="png", group=f"group{i}")
        guids.append(guid)

    # Verify all in metadata
    for guid in guids:
        assert guid in storage.metadata, f"GUID {guid} should be in metadata"

    logger.info("Multiple saves maintained metadata integrity")


def test_metadata_permissions_error_recovery(temp_storage_dir):
    """Test behavior when metadata file becomes read-only after initialization"""
    logger: Logger = session_logger
    logger.info("Testing metadata permissions error")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Save first image successfully
    test_data = b"test1"
    guid1 = storage.save_image(test_data, format="png", group="test")
    logger.info("First save successful", guid=guid1)

    # Make metadata read-only
    metadata_path = os.path.join(temp_storage_dir, "metadata.json")
    os.chmod(metadata_path, 0o444)

    try:
        # Try to save another image (should fail due to metadata write error)
        test_data2 = b"test2"
        with pytest.raises(RuntimeError) as exc_info:
            storage.save_image(test_data2, format="png", group="test")

        assert "metadata" in str(exc_info.value).lower()
        logger.info("Properly raised error when metadata cannot be updated")

    finally:
        # Restore permissions
        os.chmod(metadata_path, 0o644)


def test_empty_metadata_file(temp_storage_dir):
    """Test when metadata.json exists but is completely empty"""
    logger: Logger = session_logger
    logger.info("Testing empty metadata file")

    # Create empty metadata file
    metadata_path = os.path.join(temp_storage_dir, "metadata.json")
    with open(metadata_path, "w") as f:
        f.write("")

    # Should handle gracefully
    storage = FileStorage(storage_dir=temp_storage_dir)

    # Should work with empty metadata
    test_data = b"test after empty"
    guid = storage.save_image(test_data, format="png", group="test")
    logger.info("Recovered from empty metadata file", guid=guid)


def test_metadata_with_unexpected_structure(temp_storage_dir):
    """Test when metadata has unexpected structure (array instead of object)"""
    logger: Logger = session_logger
    logger.info("Testing metadata with unexpected structure")

    # Create metadata with array instead of object
    metadata_path = os.path.join(temp_storage_dir, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(["array", "of", "strings"], f)

    # Should handle gracefully
    storage = FileStorage(storage_dir=temp_storage_dir)

    # Should reset to empty dict and continue
    test_data = b"test after bad structure"
    guid = storage.save_image(test_data, format="png", group="test")
    logger.info("Recovered from unexpected metadata structure", guid=guid)
