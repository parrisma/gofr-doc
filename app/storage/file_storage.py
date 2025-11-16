"""File-based storage implementation

Stores images as files in a directory with GUID-based filenames.
Supports group-based segregation for access control.
"""

import uuid
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, List
from app.storage.base import ImageStorageBase
from app.config import get_default_storage_dir
from app.logger import Logger, session_logger


class FileStorage(ImageStorageBase):
    """File-based image storage using GUID filenames with group segregation"""

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize file storage

        Args:
            storage_dir: Directory to store images. If None, uses configured default from app.config
        """
        if storage_dir is None:
            storage_dir = get_default_storage_dir()
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
        """Load image metadata including group mappings"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    data = json.load(f)
                    # Validate that metadata is a dict, not a list or other type
                    if isinstance(data, dict):
                        self.metadata = data
                        self.logger.debug("Metadata loaded", images_count=len(self.metadata))
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
        """Save image metadata to disk"""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2)
            self.logger.debug("Metadata saved", images_count=len(self.metadata))
        except Exception as e:
            self.logger.error("Failed to save metadata", error=str(e))
            raise RuntimeError(f"Failed to save metadata: {str(e)}")

    def save_image(
        self, image_data: bytes, format: str = "png", group: Optional[str] = None
    ) -> str:
        """
        Save image data to disk with a unique GUID

        Args:
            image_data: Raw image bytes
            format: Image format (png, jpg, svg, pdf, etc.)
            group: Optional group name for access control

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
            "Saving image to file", guid=guid, format=format, size=len(image_data), group=group
        )

        try:
            with open(filepath, "wb") as f:
                f.write(image_data)

            # Store metadata with timestamp
            self.metadata[guid] = {
                "format": format.lower(),
                "group": group,
                "size": len(image_data),
                "created_at": datetime.utcnow().isoformat(),
            }
            self._save_metadata()

            self.logger.info("Image saved to file", guid=guid, path=str(filepath), group=group)
            return guid
        except Exception as e:
            self.logger.error("Failed to save image file", guid=guid, error=str(e))
            raise RuntimeError(f"Failed to save image: {str(e)}")

    def get_image(
        self, identifier: str, group: Optional[str] = None
    ) -> Optional[Tuple[bytes, str]]:
        """
        Retrieve image data by GUID

        Args:
            identifier: GUID string (without extension)
            group: Optional group name for access control

        Returns:
            Tuple of (image_data, format) or None if not found

        Raises:
            ValueError: If GUID format is invalid or group mismatch
        """
        # Validate GUID format
        try:
            uuid.UUID(identifier)
        except ValueError:
            self.logger.warning("Invalid GUID format", guid=identifier)
            raise ValueError(f"Invalid GUID format: {identifier}")

        # Check group access
        if identifier in self.metadata:
            stored_group = self.metadata[identifier].get("group")
            if group is not None and stored_group is not None and stored_group != group:
                self.logger.warning(
                    "Group mismatch",
                    guid=identifier,
                    requested_group=group,
                    stored_group=stored_group,
                )
                raise ValueError("Access denied: image belongs to different group")

        self.logger.debug("Retrieving image from file", guid=identifier, group=group)

        # Try common formats (prefer metadata format if available)
        formats = ["png", "jpg", "jpeg", "svg", "pdf"]
        if identifier in self.metadata:
            stored_format = self.metadata[identifier].get("format")
            if stored_format and stored_format in formats:
                formats = [stored_format] + [f for f in formats if f != stored_format]

        for ext in formats:
            filepath = self.storage_dir / f"{identifier}.{ext}"
            if filepath.exists():
                try:
                    with open(filepath, "rb") as f:
                        image_data = f.read()
                    self.logger.info(
                        "Image retrieved from file",
                        guid=identifier,
                        format=ext,
                        size=len(image_data),
                        group=group,
                    )
                    return (image_data, ext)
                except Exception as e:
                    self.logger.error("Failed to read image file", guid=identifier, error=str(e))
                    raise RuntimeError(f"Failed to read image: {str(e)}")

        self.logger.warning("Image file not found", guid=identifier)
        return None

    def delete_image(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Delete image file by GUID

        Args:
            identifier: GUID string (without extension)
            group: Optional group name for access control

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

        # Check group access
        if identifier in self.metadata:
            stored_group = self.metadata[identifier].get("group")
            if group is not None and stored_group is not None and stored_group != group:
                self.logger.warning(
                    "Group mismatch for deletion",
                    guid=identifier,
                    requested_group=group,
                    stored_group=stored_group,
                )
                raise ValueError("Access denied: image belongs to different group")

        deleted = False
        for ext in ["png", "jpg", "jpeg", "svg", "pdf"]:
            filepath = self.storage_dir / f"{identifier}.{ext}"
            if filepath.exists():
                try:
                    filepath.unlink()
                    self.logger.info("Image file deleted", guid=identifier, format=ext, group=group)
                    deleted = True
                except Exception as e:
                    self.logger.error("Failed to delete image file", guid=identifier, error=str(e))

        # Remove from metadata
        if identifier in self.metadata:
            del self.metadata[identifier]
            self._save_metadata()

        return deleted

    def list_images(self, group: Optional[str] = None) -> List[str]:
        """
        List all stored image GUIDs, optionally filtered by group

        Args:
            group: Optional group name to filter by

        Returns:
            List of GUID strings
        """
        try:
            guids = set()
            for filepath in self.storage_dir.iterdir():
                if filepath.is_file() and filepath.suffix in [
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".svg",
                    ".pdf",
                ]:
                    # Extract GUID (filename without extension)
                    guid = filepath.stem
                    try:
                        uuid.UUID(guid)
                        # Filter by group if specified
                        if group is not None:
                            if guid in self.metadata and self.metadata[guid].get("group") == group:
                                guids.add(guid)
                        else:
                            guids.add(guid)
                    except ValueError:
                        # Skip non-GUID files
                        pass
            self.logger.debug("Listed image files", count=len(guids), group=group)
            return sorted(guids)
        except Exception as e:
            self.logger.error("Failed to list image files", error=str(e))
            return []

    def exists(self, identifier: str, group: Optional[str] = None) -> bool:
        """
        Check if an image file exists and is accessible to the group

        Args:
            identifier: GUID string (without extension)
            group: Optional group name for access control

        Returns:
            True if image exists and is accessible, False otherwise
        """
        # Validate GUID format
        try:
            uuid.UUID(identifier)
        except ValueError:
            return False

        # Check group access if specified
        if group is not None and identifier in self.metadata:
            stored_group = self.metadata[identifier].get("group")
            if stored_group is not None and stored_group != group:
                return False

        # Check for any matching file with common extensions
        for ext in ["png", "jpg", "jpeg", "svg", "pdf"]:
            filepath = self.storage_dir / f"{identifier}.{ext}"
            if filepath.exists():
                return True

        return False

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
        self.logger.info("Starting purge", age_days=age_days, group=group)

        deleted_count = 0
        cutoff_time = None

        if age_days > 0:
            cutoff_time = datetime.utcnow() - timedelta(days=age_days)
            self.logger.debug("Purge cutoff time", cutoff=cutoff_time.isoformat())

        try:
            # Iterate over all files in storage directory
            for filepath in self.storage_dir.iterdir():
                if not filepath.is_file() or filepath.name == "metadata.json":
                    continue

                # Extract GUID from filename
                guid = filepath.stem
                try:
                    uuid.UUID(guid)
                except ValueError:
                    # Skip non-GUID files
                    continue

                # Check group filter
                if group is not None and guid in self.metadata:
                    stored_group = self.metadata[guid].get("group")
                    if stored_group != group:
                        continue

                # Determine file age
                should_delete = False

                if age_days == 0:
                    # Delete all (matching group if specified)
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
                        self.logger.debug("Purged image", guid=guid, file=str(filepath))
                    except Exception as e:
                        self.logger.error(
                            "Failed to delete file during purge", guid=guid, error=str(e)
                        )

            # Clean up orphaned metadata entries (entries without corresponding files)
            orphaned_guids = []
            for guid in list(self.metadata.keys()):
                # Check if file exists
                file_exists = False
                for ext in ["png", "jpg", "jpeg", "svg", "pdf"]:
                    if (self.storage_dir / f"{guid}.{ext}").exists():
                        file_exists = True
                        break

                if not file_exists:
                    # Check group filter
                    if group is not None:
                        stored_group = self.metadata[guid].get("group")
                        if stored_group != group:
                            continue

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
                "Purge completed", deleted_count=deleted_count, age_days=age_days, group=group
            )
            return deleted_count

        except Exception as e:
            self.logger.error("Purge operation failed", error=str(e))
            raise RuntimeError(f"Failed to purge images: {str(e)}")
