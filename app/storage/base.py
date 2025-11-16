"""Base storage interface for document storage

Defines the abstract interface that all storage implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Optional, List


class DocumentStorageBase(ABC):
    """Abstract base class for document storage implementations"""

    @abstractmethod
    def save_document(
        self, document_data: bytes, format: str = "json", group: Optional[str] = None
    ) -> str:
        """
        Save document data and return a unique identifier

        Args:
            document_data: Raw document bytes
            format: Document format (png, jpg, svg, pdf, json, etc.)
            group: Optional group name for access control

        Returns:
            Unique identifier (e.g., GUID, key, path) for the saved document

        Raises:
            RuntimeError: If save fails
        """
        pass

    @abstractmethod
    def get_document(self, identifier: str, group: Optional[str] = None) -> Optional[bytes]:
        """
        Retrieve document data by identifier

        Args:
            identifier: Unique identifier for the document
            group: Optional group name for access control

        Returns:
            Document bytes or None if not found

        Raises:
            ValueError: If identifier format is invalid or group mismatch
            RuntimeError: If retrieval fails
        """
        pass

    @abstractmethod
    def delete_document(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Delete document by identifier

        Args:
            identifier: Unique identifier for the document
            group: Optional group name for access control

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If identifier format is invalid or group mismatch
        """
        pass

    @abstractmethod
    def list_documents(self, group: Optional[str] = None) -> List[str]:
        """
        List all stored document identifiers

        Args:
            group: Optional group name to filter by

        Returns:
            List of identifier strings
        """
        pass

    @abstractmethod
    def exists(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Check if a document exists

        Args:
            identifier: Unique identifier for the document
            group: Optional group name for access control

        Returns:
            True if document exists, False otherwise
        """
        pass

    @abstractmethod
    def purge(self, age_days: int = 0, group: Optional[str] = None) -> int:
        """
        Delete documents older than specified age

        Args:
            age_days: Delete documents older than this many days. 0 means delete all.
            group: Optional group name to filter by

        Returns:
            Number of documents deleted

        Raises:
            RuntimeError: If purge fails
        """
        pass
