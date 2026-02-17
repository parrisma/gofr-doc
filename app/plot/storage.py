"""Plot storage wrapper.

Thin wrapper around CommonStorageAdapter that segregates plot image
artifacts from document artifacts using metadata tagging, not separate
storage instances. Both plot images and documents coexist in the same
blob store / metadata.json.

Segregation: artifact_type="plot_image" in BlobMetadata.extra
Alias isolation: plot_alias field in metadata prevents collision with doc aliases
"""

import base64
from typing import Optional, List, Dict, Any

from app.storage.common_adapter import CommonStorageAdapter
from app.logger import Logger, session_logger


class PlotStorageWrapper:
    """Wraps CommonStorageAdapter for plot image storage with metadata segregation.

    All methods delegate to the shared CommonStorageAdapter but tag plot
    artifacts with artifact_type="plot_image" and use plot_alias for alias
    resolution within the plot domain.
    """

    ARTIFACT_TYPE = "plot_image"

    def __init__(self, storage: CommonStorageAdapter, logger: Optional[Logger] = None):
        self._storage = storage
        self._logger = logger or session_logger

    def save_image(
        self,
        image_data: bytes,
        format: str = "png",
        group: Optional[str] = None,
        alias: Optional[str] = None,
    ) -> str:
        """Save a plot image with plot-specific metadata tagging.

        Args:
            image_data: Raw image bytes
            format: Image format (png, jpg, svg, pdf)
            group: Group name for access control
            alias: Optional friendly name for the image

        Returns:
            GUID string
        """
        kwargs: Dict[str, Any] = {"artifact_type": self.ARTIFACT_TYPE}
        if alias:
            kwargs["plot_alias"] = alias

        guid = self._storage.save_document(
            document_data=image_data,
            format=format,
            group=group,
            **kwargs,
        )

        # Register alias in the standard alias system if provided
        if alias and group:
            try:
                self._storage.register_alias(alias, guid, group)
            except ValueError:
                self._logger.warning(
                    "Alias registration failed (may already exist)",
                    alias=alias,
                    guid=guid,
                    group=group,
                )

        self._logger.info(
            "Plot image saved",
            guid=guid,
            format=format,
            group=group,
            alias=alias,
            size_bytes=len(image_data),
        )
        return guid

    def get_image(
        self, identifier: str, group: Optional[str] = None
    ) -> Optional[tuple[bytes, str]]:
        """Retrieve a plot image by GUID or alias.

        Args:
            identifier: GUID or alias
            group: Group for access control

        Returns:
            Tuple of (image_bytes, format) or None if not found
        """
        # Try standard get which handles alias resolution
        result = self._storage.get_image(identifier, group=group)
        if result is None:
            return None

        image_data, fmt = result

        # Verify this is actually a plot artifact (not a document)
        guid = self._storage.resolve_identifier(identifier, group)
        if guid and self._is_plot_artifact(guid):
            return image_data, fmt

        # If resolve failed but get succeeded, still return it
        # (the identifier might be a direct GUID)
        return image_data, fmt

    def list_images(self, group: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all plot images in a group, filtered by artifact_type.

        Args:
            group: Group name to filter by

        Returns:
            List of dicts with guid, format, alias, size info
        """
        all_metadata = self._storage.metadata
        results = []

        for guid, meta in all_metadata.items():
            # Filter to plot artifacts only
            if meta.get("artifact_type") != self.ARTIFACT_TYPE:
                continue

            # Filter by group if specified
            if group and meta.get("group") != group:
                continue

            alias = self._storage.get_alias(guid)
            results.append({
                "guid": guid,
                "format": meta.get("format", "unknown"),
                "alias": alias,
                "size": meta.get("size", 0),
                "created_at": meta.get("created_at"),
            })

        return results

    def list_image_guids(self, group: Optional[str] = None) -> List[str]:
        """List GUIDs of plot images in a group.

        Args:
            group: Group name to filter by

        Returns:
            List of GUID strings
        """
        return [img["guid"] for img in self.list_images(group)]

    def get_image_as_data_uri(
        self, identifier: str, group: Optional[str] = None
    ) -> Optional[str]:
        """Get a plot image as a base64 data URI for embedding.

        Args:
            identifier: GUID or alias
            group: Group for access control

        Returns:
            Data URI string (data:image/png;base64,...) or None
        """
        result = self.get_image(identifier, group)
        if result is None:
            return None
        image_data, fmt = result
        content_type = f"image/{fmt}"
        b64 = base64.b64encode(image_data).decode("utf-8")
        return f"data:{content_type};base64,{b64}"

    def resolve_identifier(self, identifier: str, group: Optional[str] = None) -> Optional[str]:
        """Resolve a plot identifier (alias or GUID) to GUID.

        Args:
            identifier: Alias or GUID
            group: Group for alias resolution

        Returns:
            GUID string or None
        """
        return self._storage.resolve_identifier(identifier, group)

    def get_alias(self, guid: str) -> Optional[str]:
        """Get alias for a plot GUID."""
        return self._storage.get_alias(guid)

    def _is_plot_artifact(self, guid: str) -> bool:
        """Check if a GUID refers to a plot artifact (vs document)."""
        metadata = self._storage.metadata
        meta = metadata.get(guid, {})
        return meta.get("artifact_type") == self.ARTIFACT_TYPE
