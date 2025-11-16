"""File-based storage implementation

Stores documents as files in a directory with GUID-based filenames.
Supports group-based segregation for access control.
"""

import uuid
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from app.storage.base import DocumentStorageBase
from app.config import get_public_storage_dir
from app.logger import Logger, session_logger


class FileStorage(DocumentStorageBase):
    """File-based document storage using GUID filenames in 'public' only"""

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize file storage

        Args:
            storage_dir: Directory to store documents. If None, uses configured default from app.config
        """
        if storage_dir is None:
            storage_dir = get_public_storage_dir()
        self.storage_dir = Path(storage_dir)
        self.metadata_file = self.storage_dir / "metadata.json"
        self.logger: Logger = session_logger

        # Create storage directory if it doesn't exist
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_metadata()
            self.logger.info("File storage initialized", directory=str(self.storage_dir))
        except Exception as e:
            self.logger.error("Failed to create storage directory", error=str(e))
            raise RuntimeError(f"Failed to create storage directory: {str(e)}")

    def _load_metadata(self) -> None:
        """Load document metadata from 'public' only"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    data = json.load(f)
                    # Validate that metadata is a dict, not a list or other type
                    if isinstance(data, dict):
                        self.metadata = data
                        self.logger.debug("Metadata loaded", documents_count=len(self.metadata))
                    else:
                        self.logger.warning(
                            "Metadata has unexpected structure, resetting to empty dict",
                            type=type(data).__name__,
                        )
                        self.metadata = {}
            except Exception as e:
                self.logger.error("Failed to load metadata", error=str(e))
                self.metadata = {}
        else:
            self.metadata = {}
            self.logger.debug("Metadata initialized as empty")

    def _save_metadata(self) -> None:
        """Save document metadata to disk"""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2)
            self.logger.debug("Metadata saved", documents_count=len(self.metadata))
        except Exception as e:
            self.logger.error("Failed to save metadata", error=str(e))
            raise RuntimeError(f"Failed to save metadata: {str(e)}")

    def save_document(self, document_data: bytes, format: str = "json") -> str:
        """
        Save document data to disk with a unique GUID

        Args:
            document_data: Raw document bytes
            format: Document format (png, jpg, svg, pdf, json, etc.)
            # Only 'public' group is supported

        Returns:
            GUID string (identifier without extension)

        Raises:
            RuntimeError: If save fails
        """
        # Generate unique GUID
        guid = str(uuid.uuid4())
        filename = f"{guid}.{format.lower()}"
        filepath = self.storage_dir / filename

        self.logger.debug(
            "Saving document to file",
            guid=guid,
            format=format,
            size=len(document_data),
            group="public",
        )

        try:
            with open(filepath, "wb") as f:
                f.write(document_data)

            # Store metadata with timestamp
            self.metadata[guid] = {
                "format": format.lower(),
                "group": "public",
                "size": len(document_data),
                "created_at": datetime.utcnow().isoformat(),
            }
            self._save_metadata()

            self.logger.info(
                "Document saved to file", guid=guid, path=str(filepath), group="public"
            )
            return guid
        except Exception as e:
            self.logger.error("Failed to save document file", guid=guid, error=str(e))
            raise RuntimeError(f"Failed to save document: {str(e)}")

    def get_document(self, identifier: str) -> Optional[bytes]:
        """
        Retrieve document data by GUID

        Args:
            identifier: GUID string (without extension)
            # Only 'public' group is supported

        Returns:
            Document bytes or None if not found

        Raises:
            ValueError: If GUID format is invalid or group mismatch
        """
        # Validate GUID format
        try:
            uuid.UUID(identifier)
        except ValueError:
            self.logger.warning("Invalid GUID format", guid=identifier)
            raise ValueError(f"Invalid GUID format: {identifier}")

        # Only 'public' group is supported

        self.logger.debug("Retrieving document from file", guid=identifier, group="public")

        # Try common formats (prefer metadata format if available)
        formats = ["png", "jpg", "jpeg", "svg", "pdf", "json"]
        if identifier in self.metadata:
            stored_format = self.metadata[identifier].get("format")
            if stored_format and stored_format in formats:
                formats = [stored_format] + [f for f in formats if f != stored_format]

        for ext in formats:
            filepath = self.storage_dir / f"{identifier}.{ext}"
            if filepath.exists():
                try:
                    with open(filepath, "rb") as f:
                        document_data = f.read()
                    self.logger.info(
                        "Document retrieved from file",
                        guid=identifier,
                        format=ext,
                        size=len(document_data),
                        group="public",
                    )
                    return document_data
                except Exception as e:
                    self.logger.error("Failed to read document file", guid=identifier, error=str(e))
                    raise RuntimeError(f"Failed to read document: {str(e)}")

        self.logger.warning("Document file not found", guid=identifier)
        return None

    def delete_document(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Delete document file by GUID

        Args:
            identifier: GUID string (without extension)
            group: Optional group name for access control (ignored)

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If group mismatch
        """
        # Validate GUID format
        try:
            uuid.UUID(identifier)
        except ValueError:
            self.logger.warning("Invalid GUID format for deletion", guid=identifier)
            return False

        # Ignore group argument, always operate on 'public'

        deleted = False
        for ext in ["png", "jpg", "jpeg", "svg", "pdf", "json"]:
            filepath = self.storage_dir / f"{identifier}.{ext}"
            if filepath.exists():
                try:
                    filepath.unlink()
                    self.logger.info(
                        "Document file deleted", guid=identifier, format=ext, group="public"
                    )
                    deleted = True
                except Exception as e:
                    self.logger.error(
                        "Failed to delete document file", guid=identifier, error=str(e)
                    )

        # Remove from metadata
        if identifier in self.metadata:
            del self.metadata[identifier]
            self._save_metadata()

        return deleted

    def list_documents(self, group: Optional[str] = None) -> List[str]:
        """
        List all stored document GUIDs, optionally filtered by group
        Searches for documents with common file extensions (.png, .jpg, .svg, .pdf, .json, etc.)

        Args:
            group: Optional group name to filter by (currently ignored, all documents are in 'public')

        Returns:
            List of GUID strings
        """
        try:
            guids = set()

            # Search in storage directory and subdirectories
            for filepath in self.storage_dir.rglob("*"):
                if filepath.is_file() and filepath.suffix in [
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".svg",
                    ".pdf",
                    ".json",
                ]:
                    # Skip metadata.json
                    if filepath.name == "metadata.json":
                        continue

                    # Extract GUID (filename without extension)
                    guid = filepath.stem
                    try:
                        uuid.UUID(guid)
                        guids.add(guid)
                    except ValueError:
                        # Skip non-GUID files
                        pass
            self.logger.debug("Listed document files", count=len(guids), group="public")
            return sorted(guids)
        except Exception as e:
            self.logger.error("Failed to list document files", error=str(e))
            return []

    def exists(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Check if a document file exists

        Args:
            identifier: GUID string (without extension)
            group: Optional group name for access control (ignored, all documents are in 'public')

        Returns:
            True if document exists, False otherwise
        """
        # Validate GUID format
        try:
            uuid.UUID(identifier)
        except ValueError:
            return False

        # Check for any matching file with common extensions in storage dir
        for ext in ["png", "jpg", "jpeg", "svg", "pdf", "json"]:
            filepath = self.storage_dir / f"{identifier}.{ext}"
            if filepath.exists():
                return True

        return False

    def purge(self, age_days: int = 0, group: Optional[str] = None) -> int:
        """
        Delete documents older than specified age

        Args:
            age_days: Delete documents older than this many days. 0 means delete all.
            group: Optional group name to filter by (ignored, all documents are in 'public')

        Returns:
            Number of documents deleted

        Raises:
            RuntimeError: If purge fails
        """
        self.logger.info("Starting purge", age_days=age_days, group="public")

        deleted_count = 0
        cutoff_time = None

        if age_days > 0:
            cutoff_time = datetime.utcnow() - timedelta(days=age_days)
            self.logger.debug("Purge cutoff time", cutoff=cutoff_time.isoformat())

        try:
            # Iterate over all files in storage directory and subdirectories
            for filepath in self.storage_dir.rglob("*"):
                if not filepath.is_file() or filepath.name == "metadata.json":
                    continue

                # Extract GUID from filename
                guid = filepath.stem
                try:
                    uuid.UUID(guid)
                except ValueError:
                    # Skip non-GUID files
                    continue

                # Determine file age
                should_delete = False

                if age_days == 0:
                    # Delete all documents
                    should_delete = True
                elif cutoff_time is not None:
                    # Check age from metadata or file modification time
                    if guid in self.metadata and "created_at" in self.metadata[guid]:
                        try:
                            created_at = datetime.fromisoformat(self.metadata[guid]["created_at"])
                            should_delete = created_at < cutoff_time
                        except (ValueError, TypeError):
                            # Fall back to file modification time if metadata is invalid
                            file_mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                            should_delete = file_mtime < cutoff_time
                    else:
                        # No metadata timestamp, use file modification time
                        file_mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                        should_delete = file_mtime < cutoff_time

                if should_delete:
                    try:
                        filepath.unlink()
                        # Remove from metadata
                        if guid in self.metadata:
                            del self.metadata[guid]
                        deleted_count += 1
                        self.logger.debug("Purged document", guid=guid, file=str(filepath))
                    except Exception as e:
                        self.logger.error(
                            "Failed to delete file during purge", guid=guid, error=str(e)
                        )

            # Clean up orphaned metadata entries (entries without corresponding files)
            orphaned_guids = []
            for guid in list(self.metadata.keys()):
                # Check if file exists
                file_exists = False
                for ext in ["png", "jpg", "jpeg", "svg", "pdf", "json"]:
                    if (self.storage_dir / f"{guid}.{ext}").exists():
                        file_exists = True
                        break

                if not file_exists:
                    # Check age filter for orphaned entries
                    should_delete = False
                    if age_days == 0:
                        should_delete = True
                    elif cutoff_time is not None and "created_at" in self.metadata[guid]:
                        try:
                            created_at = datetime.fromisoformat(self.metadata[guid]["created_at"])
                            should_delete = created_at < cutoff_time
                        except (ValueError, TypeError):
                            # If we can't parse the date, consider it for deletion
                            should_delete = True

                    if should_delete:
                        orphaned_guids.append(guid)

            # Remove orphaned metadata entries
            for guid in orphaned_guids:
                del self.metadata[guid]
                deleted_count += 1
                self.logger.debug("Removed orphaned metadata", guid=guid)

            # Save updated metadata if anything was deleted
            if deleted_count > 0:
                self._save_metadata()

            self.logger.info(
                "Purge completed", deleted_count=deleted_count, age_days=age_days, group="public"
            )
            return deleted_count

        except Exception as e:
            self.logger.error("Purge operation failed", error=str(e))
            raise RuntimeError(f"Failed to purge documents: {str(e)}")

    # ============================================================================
    # Backward compatibility wrapper methods (for test suite transition)
    # ============================================================================

    def save_image(
        self, image_data: bytes, format: str = "png", group: Optional[str] = None
    ) -> str:
        """
        Backward compatibility wrapper: save_image -> save_document
        Stores document data and returns GUID.
        """
        return self.save_document(document_data=image_data, format=format)

    def get_image(self, identifier: str, group: Optional[str] = None) -> Optional[tuple]:
        """
        Backward compatibility wrapper: get_image -> get_document
        Returns tuple of (document_bytes, format) for test compatibility.
        """
        data = self.get_document(identifier)
        if data is not None:
            fmt = self.metadata.get(identifier, {}).get("format", "png")
            return (data, fmt)
        return None

    def delete_image(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Backward compatibility wrapper: delete_image -> delete_document
        """
        return self.delete_document(identifier)

    def list_images(self, group: Optional[str] = None) -> List[str]:
        """
        Backward compatibility wrapper: list_images -> list_documents
        """
        return self.list_documents(group=group)
