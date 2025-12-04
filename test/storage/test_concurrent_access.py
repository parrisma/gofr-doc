#!/usr/bin/env python3
"""Test thread safety and concurrent access to storage"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import tempfile
import shutil
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.storage.file_storage import FileStorage
from app.logger import Logger, session_logger


@pytest.fixture
def temp_storage_dir():
    """Create a temporary storage directory for tests"""
    temp_dir = tempfile.mkdtemp(prefix="gofr_doc_concurrent_test_")
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_concurrent_saves(temp_storage_dir):
    """Test multiple threads saving images simultaneously"""
    logger: Logger = session_logger
    logger.info("Testing concurrent image saves")

    storage = FileStorage(storage_dir=temp_storage_dir)
    num_threads = 10
    guids = []
    errors = []

    def save_image(thread_id):
        try:
            test_data = f"image from thread {thread_id}".encode()
            guid = storage.save_image(test_data, format="png", group=f"thread{thread_id}")
            return guid
        except Exception as e:
            errors.append((thread_id, str(e)))
            return None

    # Save images concurrently
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(save_image, i) for i in range(num_threads)]
        for future in as_completed(futures):
            guid = future.result()
            if guid:
                guids.append(guid)

    # Check for errors
    assert len(errors) == 0, f"Concurrent saves had errors: {errors}"

    # All saves should succeed
    assert len(guids) == num_threads, f"Expected {num_threads} GUIDs, got {len(guids)}"

    # All GUIDs should be unique
    assert len(set(guids)) == num_threads, "Duplicate GUIDs generated"

    # All should be in metadata
    for guid in guids:
        assert guid in storage.metadata, f"GUID {guid} not in metadata"

    logger.info("Concurrent saves completed successfully", saved=len(guids))


def test_concurrent_save_and_retrieve(temp_storage_dir):
    """Test saving and retrieving images concurrently"""
    logger: Logger = session_logger
    logger.info("Testing concurrent save and retrieve operations")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Pre-save some images
    saved_guids = []
    for i in range(5):
        test_data = f"pre-saved image {i}".encode()
        guid = storage.save_image(test_data, format="png", group="presaved")
        saved_guids.append((guid, test_data))

    operations = []
    errors = []

    def mixed_operation(op_id):
        """Mix of save and retrieve operations"""
        try:
            if op_id % 2 == 0:
                # Save operation
                test_data = f"new image {op_id}".encode()
                guid = storage.save_image(test_data, format="png", group=f"mixed{op_id}")
                return ("save", guid)
            else:
                # Retrieve operation
                guid, expected_data = saved_guids[op_id % len(saved_guids)]
                result = storage.get_image(guid, group="presaved")
                if result:
                    retrieved_data, _ = result
                    assert retrieved_data == expected_data, f"Data mismatch for GUID {guid}"
                return ("retrieve", guid)
        except Exception as e:
            errors.append((op_id, str(e)))
            return None

    # Execute mixed operations concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(mixed_operation, i) for i in range(20)]
        for future in as_completed(futures):
            result = future.result()
            if result:
                operations.append(result)

    assert len(errors) == 0, f"Concurrent operations had errors: {errors}"
    logger.info("Concurrent save/retrieve completed", operations=len(operations))


def test_concurrent_retrieval_same_guid(temp_storage_dir):
    """Test multiple threads retrieving the same GUID simultaneously"""
    logger: Logger = session_logger
    logger.info("Testing concurrent retrieval of same GUID")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Save one image
    test_data = b"shared image data"
    guid = storage.save_image(test_data, format="png", group="shared")

    num_threads = 20
    results = []
    errors = []

    def retrieve_image(thread_id):
        try:
            result = storage.get_image(guid, group="shared")
            return result
        except Exception as e:
            errors.append((thread_id, str(e)))
            return None

    # Retrieve same image concurrently
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(retrieve_image, i) for i in range(num_threads)]
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    # All retrievals should succeed
    assert len(errors) == 0, f"Concurrent retrievals had errors: {errors}"
    assert len(results) == num_threads, f"Expected {num_threads} retrievals, got {len(results)}"

    # All should return same data
    for retrieved_data, format_type in results:
        assert retrieved_data == test_data, "Retrieved data mismatch"
        assert format_type == "png", "Format mismatch"

    logger.info("Concurrent retrievals successful", retrievals=len(results))


def test_metadata_race_condition(temp_storage_dir):
    """Test for race conditions in metadata updates"""
    logger: Logger = session_logger
    logger.info("Testing metadata race conditions")

    storage = FileStorage(storage_dir=temp_storage_dir)
    num_saves = 50

    def rapid_save(save_id):
        test_data = f"rapid save {save_id}".encode()
        return storage.save_image(test_data, format="png", group=f"rapid{save_id}")

    # Rapid concurrent saves
    with ThreadPoolExecutor(max_workers=10) as executor:
        guids = list(executor.map(rapid_save, range(num_saves)))

    # Verify metadata integrity
    assert len(guids) == num_saves, f"Expected {num_saves} GUIDs"
    assert len(storage.metadata) == num_saves, f"Metadata should have {num_saves} entries"

    # Each GUID should be in metadata
    for guid in guids:
        assert guid in storage.metadata, f"GUID {guid} missing from metadata"

    logger.info("Metadata maintained integrity under concurrent load")


@pytest.mark.asyncio
async def test_async_concurrent_operations(temp_storage_dir):
    """Test concurrent operations using asyncio"""
    logger: Logger = session_logger
    logger.info("Testing async concurrent operations")

    storage = FileStorage(storage_dir=temp_storage_dir)

    async def save_image_async(task_id):
        # Simulate async save
        await asyncio.sleep(0.01)  # Small delay
        test_data = f"async image {task_id}".encode()
        # Storage operations are synchronous, run in executor
        loop = asyncio.get_event_loop()
        guid = await loop.run_in_executor(
            None, storage.save_image, test_data, "png", f"async{task_id}"
        )
        return guid

    # Create many concurrent async tasks
    tasks = [save_image_async(i) for i in range(20)]
    guids = await asyncio.gather(*tasks)

    # All should succeed
    assert len(guids) == 20, "All async saves should succeed"
    assert len(set(guids)) == 20, "All GUIDs should be unique"

    logger.info("Async concurrent operations successful")


def test_concurrent_delete_and_save(temp_storage_dir):
    """Test concurrent delete and save operations"""
    logger: Logger = session_logger
    logger.info("Testing concurrent delete and save")

    storage = FileStorage(storage_dir=temp_storage_dir)

    # Pre-save some images
    guids_to_delete = []
    for i in range(10):
        test_data = f"to delete {i}".encode()
        guid = storage.save_image(test_data, format="png", group="deletable")
        guids_to_delete.append(guid)

    def mixed_delete_save(op_id):
        if op_id % 2 == 0 and op_id // 2 < len(guids_to_delete):
            # Delete operation
            guid = guids_to_delete[op_id // 2]
            return ("delete", storage.delete_image(guid, group="deletable"))
        else:
            # Save operation
            test_data = f"new during delete {op_id}".encode()
            guid = storage.save_image(test_data, format="png", group="newsaves")
            return ("save", guid)

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(mixed_delete_save, range(20)))

    logger.info("Concurrent delete and save completed", operations=len(results))


def test_storage_under_load(temp_storage_dir):
    """Stress test with many concurrent operations"""
    logger: Logger = session_logger
    logger.info("Testing storage under heavy load")

    storage = FileStorage(storage_dir=temp_storage_dir)
    num_operations = 100

    def random_operation(op_id):
        """Perform random storage operation"""
        import random

        op_type = random.choice(["save", "retrieve", "check"])

        if op_type == "save":
            test_data = f"load test {op_id}".encode()
            guid = storage.save_image(test_data, format="png", group=f"load{op_id % 10}")
            return ("save", guid)
        elif op_type == "retrieve":
            # Try to retrieve a GUID (may not exist)
            fake_guid = f"{op_id:08x}-0000-0000-0000-000000000000"
            result = storage.get_image(fake_guid)
            return ("retrieve", result is not None)
        else:
            # Just check metadata
            return ("check", len(storage.metadata))

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(random_operation, range(num_operations)))
    duration = time.time() - start_time

    logger.info(
        "Storage handled heavy load",
        operations=len(results),
        duration_seconds=f"{duration:.2f}",
        ops_per_second=f"{len(results) / duration:.1f}",
    )

    # Verify storage is still functional
    test_data = b"post-load test"
    guid = storage.save_image(test_data, format="png", group="postload")
    assert guid is not None, "Storage should still work after load test"
