"""Document storage module

Provides abstract base class and concrete implementations for document storage.
"""

from app.storage.base import DocumentStorageBase
from app.storage.file_storage import FileStorage
from app.config import get_default_storage_dir
from typing import Optional

# Global storage instance
_storage: Optional[DocumentStorageBase] = None


def get_storage(storage_dir: Optional[str] = None) -> DocumentStorageBase:
    """
    Get or create the global storage instance

    Args:
        storage_dir: Directory for file storage (only used on first call).
                    If None, uses configured default from app.config

    Returns:
        DocumentStorageBase implementation (currently FileStorage)
    """
    global _storage
    if _storage is None:
        if storage_dir is None:
            storage_dir = get_default_storage_dir()
        _storage = FileStorage(storage_dir)
    return _storage


def set_storage(storage: Optional[DocumentStorageBase]) -> None:
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
    "DocumentStorageBase",
    "FileStorage",
    "get_storage",
    "set_storage",
    "reset_storage",
]
