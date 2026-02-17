#!/usr/bin/env python3
"""Unit tests for stock image hosting endpoints.

Tests the GET /images (listing) and GET /images/{path} (serving) endpoints
added to GofrDocWebServer. Images are served publicly (no auth required)
from a configurable directory backed by a Docker volume in production.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from fastapi.testclient import TestClient
from app.web_server.web_server import GofrDocWebServer


@pytest.fixture
def images_dir(tmp_path):
    """Create a temporary images directory with test files."""
    img_dir = tmp_path / "images"
    img_dir.mkdir()

    repo_root = Path(__file__).resolve().parents[2]
    piggy_bank_jpg = repo_root / "test" / "assets" / "images" / "piggy-bank.jpg"
    if not piggy_bank_jpg.is_file():
        raise RuntimeError(f"Missing test asset: {piggy_bank_jpg}")

    # Create some test image files (content doesn't matter for serving tests)
    (img_dir / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    (img_dir / "piggy-bank.jpg").write_bytes(piggy_bank_jpg.read_bytes())

    # Create subdirectory with images
    logos_dir = img_dir / "logos"
    logos_dir.mkdir()
    (logos_dir / "acme.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    (logos_dir / "brand.svg").write_text("<svg></svg>")

    # Create a nested subdirectory
    charts_dir = img_dir / "charts" / "q1"
    charts_dir.mkdir(parents=True)
    (charts_dir / "revenue.webp").write_bytes(b"RIFF" + b"\x00" * 16)

    # Create a non-image file (should be excluded from listing and rejected on serve)
    (img_dir / "readme.txt").write_text("not an image")

    return img_dir


@pytest.fixture
def empty_images_dir(tmp_path):
    """Create an empty images directory."""
    img_dir = tmp_path / "images_empty"
    img_dir.mkdir()
    return img_dir


@pytest.fixture
def client(images_dir, auth_service):
    """Create a TestClient with a populated images directory."""
    server = GofrDocWebServer(
        images_dir=str(images_dir),
        auth_service=auth_service,
    )
    return TestClient(server.app)


@pytest.fixture
def empty_client(empty_images_dir, auth_service):
    """Create a TestClient with an empty images directory."""
    server = GofrDocWebServer(
        images_dir=str(empty_images_dir),
        auth_service=auth_service,
    )
    return TestClient(server.app)


@pytest.fixture
def missing_dir_client(tmp_path, auth_service):
    """Create a TestClient where the images directory does not exist."""
    server = GofrDocWebServer(
        images_dir=str(tmp_path / "nonexistent"),
        auth_service=auth_service,
    )
    return TestClient(server.app)


# ============================================================================
# Listing endpoint: GET /images
# ============================================================================


class TestImageListing:
    """Tests for the GET /images listing endpoint."""

    def test_images_list_with_files(self, client):
        """Listing returns all image files with correct count."""
        response = client.get("/images")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        images = data["data"]["images"]
        count = data["data"]["count"]
        assert count == len(images)
        assert (
            count == 5
        )  # hero.png, piggy-bank.jpg, logos/acme.png, logos/brand.svg, charts/q1/revenue.webp

    def test_images_list_preserves_subdirs(self, client):
        """Subdirectory paths are preserved in listing."""
        response = client.get("/images")
        images = response.json()["data"]["images"]
        assert "logos/acme.png" in images
        assert "logos/brand.svg" in images
        assert "charts/q1/revenue.webp" in images

    def test_images_list_excludes_non_images(self, client):
        """Non-image files (e.g. .txt) are excluded from listing."""
        response = client.get("/images")
        images = response.json()["data"]["images"]
        for img in images:
            assert not img.endswith(".txt"), f"Non-image file listed: {img}"

    def test_images_list_empty(self, empty_client):
        """Listing with no images returns empty list, not an error."""
        response = empty_client.get("/images")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["images"] == []
        assert data["data"]["count"] == 0

    def test_images_list_missing_dir(self, missing_dir_client):
        """Listing when images dir does not exist returns empty list."""
        response = missing_dir_client.get("/images")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["images"] == []
        assert data["data"]["count"] == 0


# ============================================================================
# Serving endpoint: GET /images/{path}
# ============================================================================


class TestImageServing:
    """Tests for the GET /images/{path} serving endpoint."""

    def test_images_serve_png(self, client):
        """Serving a PNG returns 200 with correct content-type."""
        response = client.get("/images/hero.png")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert "max-age=3600" in response.headers.get("cache-control", "")

    def test_images_serve_jpg(self, client):
        """Serving a JPG returns correct content-type."""
        response = client.get("/images/piggy-bank.jpg")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"

    def test_images_serve_svg(self, client):
        """Serving an SVG returns image/svg+xml content-type."""
        response = client.get("/images/logos/brand.svg")
        assert response.status_code == 200
        assert "image/svg+xml" in response.headers["content-type"]

    def test_images_serve_nested(self, client):
        """Serving a deeply nested image works correctly."""
        response = client.get("/images/charts/q1/revenue.webp")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"

    def test_images_404_missing(self, client):
        """Request for non-existent image returns 404."""
        response = client.get("/images/does-not-exist.png")
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert detail["error"] == "IMAGE_NOT_FOUND"

    def test_images_400_traversal(self, client):
        """Path traversal attempts are rejected -- image is never served from outside images_dir."""
        # FastAPI normalizes '..' in URL paths, so test both the HTTP level
        # and that the path guard works for any path that escapes the root.
        traversal_paths = [
            "/images/../../../etc/passwd",
            "/images/..%2F..%2Fetc/passwd",
        ]
        for path in traversal_paths:
            response = client.get(path)
            # Must NOT return 200 with file contents from outside images_dir
            assert response.status_code in (
                400,
                404,
                422,
            ), f"Traversal path {path} should be rejected, got {response.status_code}"

    def test_images_resolve_rejects_traversal(self, images_dir, auth_service):
        """Internal _resolve_image_path rejects '..' segments directly."""
        from fastapi import HTTPException

        server = GofrDocWebServer(
            images_dir=str(images_dir),
            auth_service=auth_service,
        )
        with pytest.raises(HTTPException) as exc_info:
            server._resolve_image_path("../../etc/passwd")
        assert exc_info.value.status_code == 400

    def test_images_400_non_image(self, client):
        """Request for non-image file extension returns 400."""
        response = client.get("/images/readme.txt")
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["error"] == "INVALID_IMAGE_TYPE"

    def test_images_no_auth_required(self, images_dir, auth_service):
        """Image endpoints work without any auth headers (even when auth is required for other endpoints)."""
        server = GofrDocWebServer(
            images_dir=str(images_dir),
            require_auth=True,
            auth_service=auth_service,
        )
        client = TestClient(server.app)
        # No auth headers -- should still work
        response = client.get("/images")
        assert response.status_code == 200
        response = client.get("/images/hero.png")
        assert response.status_code == 200
