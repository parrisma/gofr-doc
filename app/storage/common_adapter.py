"""Adapter for gofr-common storage

Adapts the gofr-common storage implementation to the gofr-doc DocumentStorageBase interface.
"""

from typing import Optional, List
from pathlib import Path
import logging
import uuid

from app.storage.base import DocumentStorageBase
from gofr_common.storage.file_storage import FileStorage as CommonFileStorage
from gofr_common.storage.exceptions import (
    PermissionDeniedError as CommonPermissionDeniedError,
    StorageError,
    ResourceNotFoundError,
)

logger = logging.getLogger("storage.adapter")


class CommonStorageAdapter(DocumentStorageBase):
    """Adapter for gofr-common FileStorage to DocumentStorageBase interface"""

    DEFAULT_GROUP = "public"

    def __init__(self, storage_dir: str | Path):
        """
        Initialize adapter with gofr-common FileStorage

        Args:
            storage_dir: Directory to store documents
        """
        self._storage = CommonFileStorage(storage_dir)
        # Keep track of metadata for format info (same approach as old FileStorage)
        self._format_cache = {}
        logger.info("CommonStorageAdapter initialized", extra={"directory": str(storage_dir)})

    def save_document(
        self, document_data: bytes, format: str = "json", group: Optional[str] = None, **kwargs
    ) -> str:
        """
        Save document data using common storage

        Args:
            document_data: Raw document bytes
            format: Document format (png, jpg, svg, pdf, json, etc.)
            group: Optional group name for access control (defaults to 'public')
            **kwargs: Additional metadata fields forwarded to BlobMetadata.extra
                      (e.g. artifact_type="plot_image", plot_alias="my-chart")

        Returns:
            GUID string (identifier without extension)

        Raises:
            RuntimeError: If save fails
        """
        if group is None:
            group = self.DEFAULT_GROUP
        try:
            guid = self._storage.save(document_data, format, group, **kwargs)
            self._format_cache[guid] = format.lower()
            return guid
        except StorageError as e:
            raise RuntimeError(f"Failed to save document: {str(e)}") from e

    def get_document(self, identifier: str, group: Optional[str] = None) -> Optional[bytes]:
        """
        Retrieve document data by identifier

        Args:
            identifier: GUID string (without extension) or alias
            group: Optional group name for access control

        Returns:
            Document bytes or None if not found

        Raises:
            ValueError: If identifier format is invalid or group mismatch
        """
        try:
            result = self._storage.get(identifier, group)
            if result is not None:
                data, fmt = result
                return data
            return None
        except CommonPermissionDeniedError as e:
            # Convert to ValueError for interface compatibility
            raise ValueError(str(e)) from e
        except ResourceNotFoundError:
            return None
        except StorageError as e:
            raise RuntimeError(f"Failed to retrieve document: {str(e)}") from e

    def delete_document(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Delete document by identifier

        Args:
            identifier: GUID string (without extension) or alias
            group: Optional group name for access control

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If group mismatch
        """
        try:
            deleted = self._storage.delete(identifier, group)
            if deleted and identifier in self._format_cache:
                del self._format_cache[identifier]
            return deleted
        except CommonPermissionDeniedError as e:
            raise ValueError(str(e)) from e

    def list_documents(self, group: Optional[str] = None) -> List[str]:
        """
        List all stored document identifiers

        Args:
            group: Optional group name to filter by

        Returns:
            List of identifier strings
        """
        return self._storage.list(group)

    def exists(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Check if a document exists

        Args:
            identifier: Unique identifier for the document
            group: Optional group name for access control

        Returns:
            True if document exists, False otherwise
        """
        return self._storage.exists(identifier, group)

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
        try:
            return self._storage.purge(age_days, group)
        except Exception as e:
            raise RuntimeError(f"Failed to purge documents: {str(e)}") from e

    # ============================================================================
    # Alias support methods (delegating to common storage)
    # ============================================================================

    def resolve_identifier(self, identifier: str, group: Optional[str] = None) -> Optional[str]:
        """
        Resolve alias or GUID to GUID

        Args:
            identifier: Alias or GUID string
            group: Optional group name for alias resolution

        Returns:
            GUID string if found, None otherwise
        """
        # Try as GUID first
        try:
            uuid.UUID(identifier)
            return identifier
        except ValueError:
            pass

        # Try as alias using internal maps of the common storage
        if hasattr(self._storage, "_alias_to_guid"):
            if group and group in self._storage._alias_to_guid:
                return self._storage._alias_to_guid[group].get(identifier)

        return None

    def register_alias(self, alias: str, guid: str, group: str) -> None:
        """
        Register an alias for a GUID

        Args:
            alias: Alias string (3-64 chars, alphanumeric with hyphens/underscores)
            guid: GUID to associate with alias
            group: Group name for isolation

        Raises:
            ValueError: If alias format invalid or already exists
        """
        self._storage.register_alias(alias, guid, group)

    def unregister_alias(self, alias: str, group: str) -> bool:
        """
        Remove an alias registration

        Args:
            alias: Alias to remove
            group: Group name

        Returns:
            True if removed, False if not found
        """
        if not hasattr(self._storage, "_alias_to_guid"):
            return False

        if group not in self._storage._alias_to_guid:
            return False

        if alias not in self._storage._alias_to_guid[group]:
            return False

        guid = self._storage._alias_to_guid[group][alias]

        # Remove from metadata
        try:
            metadata = self._storage.metadata_repo.get(guid)
            if metadata and "aliases" in metadata.extra:
                aliases = metadata.extra["aliases"]
                if alias in aliases:
                    aliases.remove(alias)
                    metadata.extra["aliases"] = aliases
                    self._storage.metadata_repo.save(metadata)

            # Rebuild maps to reflect changes
            self._storage._rebuild_alias_maps()
            return True
        except Exception as e:
            logger.error(f"Failed to unregister alias: {e}")
            return False

    def get_alias(self, guid: str) -> Optional[str]:
        """
        Get alias for a GUID

        Args:
            guid: GUID string

        Returns:
            Alias if registered, None otherwise
        """
        return self._storage.get_alias(guid)

    def list_aliases(self, group: str) -> dict:
        """
        List all aliases in a group

        Args:
            group: Group name

        Returns:
            Dictionary mapping alias -> guid
        """
        if hasattr(self._storage, "_alias_to_guid"):
            if group in self._storage._alias_to_guid:
                return self._storage._alias_to_guid[group].copy()
        return {}

    # ============================================================================
    # Backward compatibility wrapper methods (for test suite transition)
    # ============================================================================

    def save_image(
        self, image_data: bytes, format: str = "png", group: Optional[str] = None
    ) -> str:
        """
        Backward compatibility wrapper: save_image -> save_document
        """
        return self.save_document(document_data=image_data, format=format, group=group)

    def get_image(self, identifier: str, group: Optional[str] = None) -> Optional[tuple]:
        """
        Backward compatibility wrapper: get_image -> get_document
        Returns tuple of (document_bytes, format) for test compatibility.
        """
        try:
            result = self._storage.get(identifier, group)
            if result is not None:
                return result  # Already returns (data, format)
            return None
        except CommonPermissionDeniedError as e:
            raise ValueError(str(e)) from e

    def delete_image(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Backward compatibility wrapper: delete_image -> delete_document
        """
        return self.delete_document(identifier, group=group)

    def list_images(self, group: Optional[str] = None) -> List[str]:
        """
        Backward compatibility wrapper: list_images -> list_documents
        """
        return self.list_documents(group=group)

    # ============================================================================
    # Metadata access helpers (for test compatibility)
    # ============================================================================

    @property
    def metadata(self) -> dict:
        """
        Access metadata for backward compatibility with tests.
        Returns a dict-like view of metadata keyed by GUID.
        """
        # Build a dict from the metadata repo
        result = {}
        for guid in self._storage.list(None):
            meta = self._storage.metadata_repo.get(guid)
            if meta:
                result[guid] = {
                    "format": meta.format,
                    "group": meta.group,
                    "size": meta.size,
                    "created_at": meta.created_at,
                    **meta.extra,
                }
        return result
