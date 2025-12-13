"""Document storage module

Provides abstract base class and concrete implementations for document storage.
Uses gofr-common storage as the default implementation via CommonStorageAdapter.
"""

from app.storage.base import DocumentStorageBase
from app.storage.file_storage import FileStorage
from app.storage.common_adapter import CommonStorageAdapter
from app.config import get_default_storage_dir
from typing import Optional
import os

# Global storage instance
_storage: Optional[DocumentStorageBase] = None

# Environment variable to choose storage implementation
# Set GOFR_DOC_USE_LEGACY_STORAGE=1 to use old FileStorage instead of CommonStorageAdapter
USE_LEGACY_STORAGE = os.environ.get("GOFR_DOC_USE_LEGACY_STORAGE", "").lower() in ("1", "true", "yes")


def get_storage(storage_dir: Optional[str] = None) -> DocumentStorageBase:
    """
    Get or create the global storage instance

    Args:
        storage_dir: Directory for file storage (only used on first call).
                    If None, uses configured default from app.config

    Returns:
        DocumentStorageBase implementation (CommonStorageAdapter by default, 
        or legacy FileStorage if GOFR_DOC_USE_LEGACY_STORAGE=1)
    """
    global _storage
    if _storage is None:
        if storage_dir is None:
            storage_dir = get_default_storage_dir()
        if USE_LEGACY_STORAGE:
            _storage = FileStorage(storage_dir)
        else:
            _storage = CommonStorageAdapter(storage_dir)
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
    "CommonStorageAdapter",
    "get_storage",
    "set_storage",
    "reset_storage",
]
