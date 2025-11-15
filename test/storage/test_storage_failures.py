#!/usr/bin/env python3
"""Test storage resilience when write operations fail"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from app.storage.file_storage import FileStorage
from app.logger import Logger, session_logger


@pytest.fixture
def temp_storage_dir():
    """Create a temporary storage directory for tests"""
    temp_dir = tempfile.mkdtemp(prefix="doco_storage_test_")
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_storage_write_failure_permission_denied(temp_storage_dir):
    """Test handling when storage directory becomes read-only"""
    logger: Logger = session_logger
    logger.info("Testing storage write failure with permission denied")

    # Create storage instance
    storage = FileStorage(storage_dir=temp_storage_dir)

    # Save an image successfully first
    test_data = b"fake image data"
    guid = storage.save_image(test_data, format="png", group="test")
    logger.info("Initial image saved successfully", guid=guid)

    # Make directory read-only
    os.chmod(temp_storage_dir, 0o444)

    try:
        # Try to save another image (should fail)
        with pytest.raises(RuntimeError) as exc_info:
            storage.save_image(test_data, format="png", group="test")

        assert "Failed to save image" in str(exc_info.value) or "Permission denied" in str(
            exc_info.value
        )
        logger.info("Storage correctly raised RuntimeError on write failure")

    finally:
        # Restore permissions for cleanup
        os.chmod(temp_storage_dir, 0o755)


def test_storage_metadata_write_failure():
    """Test handling when metadata.json cannot be written"""
    logger: Logger = session_logger
    logger.info("Testing metadata write failure")

    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorage(storage_dir=temp_dir)

        # Mock the open function to fail on metadata write
        original_open = open

        def mock_open_failure(*args, **kwargs):
            # Allow reading, fail on writing metadata.json
            if len(args) > 0 and "metadata.json" in str(args[0]) and "w" in str(args[1]):
                raise PermissionError("Simulated metadata write failure")
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_failure):
            test_data = b"test image"

            # Should raise RuntimeError when metadata cannot be saved
            with pytest.raises(RuntimeError) as exc_info:
                storage.save_image(test_data, format="png", group="test")

            assert "metadata" in str(exc_info.value).lower()
            logger.info("Storage correctly handled metadata write failure")


def test_storage_disk_full_simulation(temp_storage_dir):
    """Test handling when disk is full"""
    logger: Logger = session_logger
    logger.info("Testing disk full simulation")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Create very large data that might trigger disk space issues
    # In real scenario, this would need actual disk full condition
    # Here we'll mock the write to simulate OSError

    with patch("builtins.open", side_effect=OSError("[Errno 28] No space left on device")):
        test_data = b"test image"

        with pytest.raises((RuntimeError, OSError)) as exc_info:
            storage.save_image(test_data, format="png", group="test")

        logger.info("Storage handled disk full condition", error=str(exc_info.value))


def test_storage_retrieve_from_readonly_directory(temp_storage_dir):
    """Test that retrieval still works when directory is read-only (no write permission)"""
    logger: Logger = session_logger
    logger.info("Testing retrieval from read-only storage")

    # Create storage and save an image
    storage = FileStorage(storage_dir=temp_storage_dir)
    test_data = b"retrieval test data"
    guid = storage.save_image(test_data, format="png", group="test")
    logger.info("Image saved for retrieval test", guid=guid)

    # Make directory read-only (r-xr-xr-x = 0o555, allows read+execute but not write)
    os.chmod(temp_storage_dir, 0o555)

    try:
        # Retrieval should still work (read operations don't need write permission)
        result = storage.get_image(guid, group="test")

        assert result is not None, "Image not found"
        retrieved_data, format_type = result
        assert retrieved_data == test_data, "Retrieved data doesn't match"
        assert format_type == "png", "Format doesn't match"
        logger.info("Retrieval works from read-only directory")

    finally:
        # Restore permissions
        os.chmod(temp_storage_dir, 0o755)


def test_storage_partial_write_recovery(temp_storage_dir):
    """Test recovery when image write completes but metadata write fails"""
    logger: Logger = session_logger
    logger.info("Testing partial write recovery")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Track files before operation
    files_before = set(os.listdir(temp_storage_dir))

    # Simulate metadata write failure after image is written
    original_save_metadata = storage._save_metadata

    def failing_save_metadata():
        raise RuntimeError("Simulated metadata failure")

    storage._save_metadata = failing_save_metadata

    try:
        test_data = b"partial write test"
        with pytest.raises(RuntimeError):
            storage.save_image(test_data, format="png", group="test")

        # Check that we don't have orphaned image files (or they're cleaned up)
        files_after = set(os.listdir(temp_storage_dir))
        new_files = files_after - files_before

        # Filter out metadata.json
        new_image_files = [f for f in new_files if not f.endswith("metadata.json")]

        logger.info(
            "Partial write handled", orphaned_files=len(new_image_files), files=new_image_files
        )

        # Note: Current implementation may leave orphaned files
        # This test documents the behavior; future enhancement could add cleanup

    finally:
        storage._save_metadata = original_save_metadata


def test_storage_initialization_failure():
    """Test handling when storage directory cannot be created"""
    logger: Logger = session_logger
    logger.info("Testing storage initialization failure")

    # Try to create storage in a path that requires root permissions
    with pytest.raises(RuntimeError) as exc_info:
        FileStorage(storage_dir="/root/impossible_path/storage")

    assert "Failed to create storage directory" in str(exc_info.value)
    logger.info("Storage initialization failure handled correctly")
