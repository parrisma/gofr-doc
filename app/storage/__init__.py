"""Image storage module

Provides abstract base class and concrete implementations for image storage.
"""

from app.storage.base import ImageStorageBase
from app.storage.file_storage import FileStorage
from app.config import get_default_storage_dir
from typing import Optional

# Global storage instance
_storage: Optional[ImageStorageBase] = None


def get_storage(storage_dir: Optional[str] = None) -> ImageStorageBase:
    """
    Get or create the global storage instance

    Args:
        storage_dir: Directory for file storage (only used on first call).
                    If None, uses configured default from app.config

    Returns:
        ImageStorageBase implementation (currently FileStorage)
    """
    global _storage
    if _storage is None:
        if storage_dir is None:
            storage_dir = get_default_storage_dir()
        _storage = FileStorage(storage_dir)
    return _storage


def set_storage(storage: Optional[ImageStorageBase]) -> None:
    """
    Set a custom storage implementation or reset to None

    Args:
        storage: Custom storage implementation, or None to reset
    """
    global _storage
    _storage = storage


def reset_storage() -> None:
    """Reset the global storage instance (useful for testing)"""
    global _storage
    _storage = None


__all__ = [
    "ImageStorageBase",
    "FileStorage",
    "get_storage",
    "set_storage",
    "reset_storage",
]
