"""Base storage interface for image storage

Defines the abstract interface that all storage implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, List


class ImageStorageBase(ABC):
    """Abstract base class for image storage implementations"""

    @abstractmethod
    def save_image(
        self, image_data: bytes, format: str = "png", group: Optional[str] = None
    ) -> str:
        """
        Save image data and return a unique identifier

        Args:
            image_data: Raw image bytes
            format: Image format (png, jpg, svg, pdf, etc.)
            group: Optional group name for access control

        Returns:
            Unique identifier (e.g., GUID, key, path) for the saved image

        Raises:
            RuntimeError: If save fails
        """
        pass

    @abstractmethod
    def get_image(
        self, identifier: str, group: Optional[str] = None
    ) -> Optional[Tuple[bytes, str]]:
        """
        Retrieve image data by identifier

        Args:
            identifier: Unique identifier for the image
            group: Optional group name for access control

        Returns:
            Tuple of (image_data, format) or None if not found

        Raises:
            ValueError: If identifier format is invalid or group mismatch
            RuntimeError: If retrieval fails
        """
        pass

    @abstractmethod
    def delete_image(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Delete image by identifier

        Args:
            identifier: Unique identifier for the image
            group: Optional group name for access control

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If identifier format is invalid or group mismatch
        """
        pass

    @abstractmethod
    def list_images(self, group: Optional[str] = None) -> List[str]:
        """
        List all stored image identifiers

        Args:
            group: Optional group name to filter by

        Returns:
            List of identifier strings
        """
        pass

    @abstractmethod
    def exists(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Check if an image exists

        Args:
            identifier: Unique identifier for the image
            group: Optional group name for access control

        Returns:
            True if image exists, False otherwise
        """
        pass

    @abstractmethod
    def purge(self, age_days: int = 0, group: Optional[str] = None) -> int:
        """
        Delete images older than specified age

        Args:
            age_days: Delete images older than this many days. 0 means delete all.
            group: Optional group name to filter by

        Returns:
            Number of images deleted

        Raises:
            RuntimeError: If purge fails
        """
        pass
