"""Image URL validation for document fragments.

Validates image URLs at add time (not render time) to provide immediate feedback
about accessibility, content-type, and size constraints.
"""

import httpx
from dataclasses import dataclass
from typing import Optional
from app.logger import Logger


@dataclass
class ImageValidationResult:
    """Result of image URL validation."""

    valid: bool
    url: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    content_type: Optional[str] = None
    content_length: Optional[int] = None
    details: Optional[dict] = None


class ImageURLValidator:
    """Validates image URLs at add time (not render time)."""

    ALLOWED_CONTENT_TYPES = {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/gif",
        "image/webp",
        "image/svg+xml",
    }

    DEFAULT_MAX_SIZE_MB = 10
    DEFAULT_TIMEOUT_SECONDS = 10

    def __init__(
        self,
        max_size_mb: int = DEFAULT_MAX_SIZE_MB,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        logger: Optional[Logger] = None,
    ):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.timeout_seconds = timeout_seconds
        self.logger = logger

    async def validate_image_url(
        self, url: str, require_https: bool = True
    ) -> ImageValidationResult:
        """Validate image URL and return detailed result.

        Args:
            url: Image URL to validate
            require_https: If True, only HTTPS URLs allowed

        Returns:
            ImageValidationResult with validation status and details
        """
        # 1. Scheme validation
        if require_https and not url.startswith("https://"):
            return ImageValidationResult(
                valid=False,
                url=url,
                error_code="INVALID_IMAGE_URL",
                error_message="Image URL must use HTTPS protocol (require_https=true)",
                details={
                    "reason": "Non-HTTPS URL with require_https=true",
                    "recovery": "Use an HTTPS URL or set require_https=false",
                },
            )

        if not url.startswith(("http://", "https://")):
            return ImageValidationResult(
                valid=False,
                url=url,
                error_code="INVALID_IMAGE_URL",
                error_message="Image URL must use HTTP or HTTPS protocol",
                details={
                    "reason": "Invalid URL scheme",
                    "recovery": "Provide a valid HTTP or HTTPS URL",
                },
            )

        # 2. HEAD request to validate accessibility and content-type
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                if self.logger:
                    self.logger.info("Validating image URL", url=url)

                response = await client.head(url, follow_redirects=True)

                # Check status code
                if response.status_code != 200:
                    return ImageValidationResult(
                        valid=False,
                        url=url,
                        error_code="IMAGE_URL_NOT_ACCESSIBLE",
                        error_message=f"Image URL returned HTTP {response.status_code}",
                        details={
                            "status_code": response.status_code,
                            "reason": f"HTTP {response.status_code}",
                            "recovery": "Verify the URL is correct and accessible. Test it in a browser.",
                        },
                    )

                # 3. Content-Type validation
                content_type = (
                    response.headers.get("content-type", "").split(";")[0].strip().lower()
                )
                if content_type not in self.ALLOWED_CONTENT_TYPES:
                    return ImageValidationResult(
                        valid=False,
                        url=url,
                        error_code="INVALID_IMAGE_CONTENT_TYPE",
                        error_message="URL does not return a valid image content-type",
                        content_type=content_type,
                        details={
                            "content_type": content_type,
                            "allowed_types": list(self.ALLOWED_CONTENT_TYPES),
                            "recovery": f"Ensure the URL points to an image file. Allowed types: {', '.join(self.ALLOWED_CONTENT_TYPES)}",
                        },
                    )

                # 4. Size check
                content_length = response.headers.get("content-length")
                if content_length:
                    content_length = int(content_length)
                    if content_length > self.max_size_bytes:
                        return ImageValidationResult(
                            valid=False,
                            url=url,
                            error_code="IMAGE_TOO_LARGE",
                            error_message="Image size exceeds maximum allowed size",
                            content_type=content_type,
                            content_length=content_length,
                            details={
                                "content_length": content_length,
                                "max_size_bytes": self.max_size_bytes,
                                "max_size_mb": self.max_size_bytes / (1024 * 1024),
                                "recovery": "Use a smaller image or compress the image before uploading",
                            },
                        )

                # Success
                if self.logger:
                    self.logger.info(
                        "Image URL validated successfully",
                        url=url,
                        content_type=content_type,
                        content_length=content_length,
                    )

                return ImageValidationResult(
                    valid=True,
                    url=url,
                    content_type=content_type,
                    content_length=content_length,
                )

        except httpx.TimeoutException:
            return ImageValidationResult(
                valid=False,
                url=url,
                error_code="IMAGE_URL_TIMEOUT",
                error_message=f"Image URL validation timed out after {self.timeout_seconds} seconds",
                details={
                    "timeout_seconds": self.timeout_seconds,
                    "recovery": "Check if the URL is slow or unreachable. Try a different URL or ensure network connectivity.",
                },
            )

        except httpx.HTTPError as exc:
            return ImageValidationResult(
                valid=False,
                url=url,
                error_code="IMAGE_URL_ERROR",
                error_message=f"Error accessing image URL: {str(exc)}",
                details={
                    "error": str(exc),
                    "recovery": "Verify the URL is accessible and try again",
                },
            )

        except Exception as exc:
            return ImageValidationResult(
                valid=False,
                url=url,
                error_code="IMAGE_VALIDATION_ERROR",
                error_message=f"Unexpected error validating image URL: {str(exc)}",
                details={
                    "error": str(exc),
                    "recovery": "Check the URL format and try again",
                },
            )
