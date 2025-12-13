"""Integration test for image fragment rendering in documents.

This test verifies that images added via add_image_fragment actually appear
in the rendered document output, catching issues like the HEAD/GET HTTP method
bug that would cause image validation to pass but rendering to fail.
"""

import base64
import io
import json
import os
from typing import Any, Dict

import httpx
import pypdf
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.logger import Logger, session_logger

# MCP server configuration
MCP_PORT = os.environ.get("GOFR_DOC_MCP_PORT", "8040")
MCP_URL = f"http://localhost:{MCP_PORT}/mcp/"


def skip_if_mcp_unavailable(func):
    """Decorator to skip tests if MCP server is unavailable."""
    import functools

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            response = httpx.get(MCP_URL, timeout=2.0)
            if response.status_code >= 500:
                pytest.skip("MCP server is unavailable (returned 5xx status)")
        except Exception as e:
            pytest.skip(f"MCP server is unavailable: {type(e).__name__}")
        return await func(*args, **kwargs)

    return wrapper


def _parse_json_response(result: Any) -> Dict[str, Any]:
    """Parse JSON response from MCP tool."""
    if hasattr(result, "content") and len(result.content) > 0:
        text = result.content[0].text
        return json.loads(text)
    return {}


@pytest.fixture
def logger() -> Logger:
    """Provide logger for tests."""
    return session_logger


# ==============================================================================
# Integration Test: Image Fragment Rendering
# ==============================================================================


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_image_fragment_appears_in_rendered_html(logger, mcp_headers, image_server):
    """Verify that an added image fragment actually appears in the rendered HTML document.

    This test catches issues where:
    - Image validation passes but rendering fails
    - HTTP method issues (HEAD vs GET) prevent image download
    - Image URL is stored but not properly included in rendering
    """
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Step 1: Create a document session
            create_result = await session.call_tool(
                "create_document_session",
                arguments={"template_id": "basic_report", "alias": "test_image_rendering-12"},
            )
            create_response = _parse_json_response(create_result)
            assert create_response["status"] == "success", "Failed to create session"
            session_id = create_response["data"]["session_id"]
            logger.info(f"Created session: {session_id}")

            # Step 2: Set global parameters (title, author)
            params_result = await session.call_tool(
                "set_global_parameters",
                arguments={
                    "session_id": session_id,
                    "parameters": {
                        "title": "Image Test Document",
                        "author": "Test Suite",
                    },
                },
            )
            params_response = _parse_json_response(params_result)
            assert params_response["status"] == "success", "Failed to set parameters"

            # Step 3: Add an image fragment from local test server
            image_url = image_server.get_url("graph.png")
            logger.info(f"Adding image from URL: {image_url}")

            add_image_result = await session.call_tool(
                "add_image_fragment",
                arguments={
                    "session_id": session_id,
                    "image_url": image_url,
                    "title": "Test Graph",
                    "width": 400,
                    "alt_text": "Test graph visualization",
                    "require_https": False,  # Local server uses HTTP
                },
            )
            add_image_response = _parse_json_response(add_image_result)
            assert (
                add_image_response["status"] == "success"
            ), f"Failed to add image: {add_image_response.get('message')}"
            fragment_guid = add_image_response["data"]["fragment_instance_guid"]
            logger.info(f"Image fragment added: {fragment_guid}")

            # Step 4: Render document to HTML
            render_result = await session.call_tool(
                "get_document",
                arguments={
                    "session_id": session_id,
                    "format": "html",
                },
            )
            render_response = _parse_json_response(render_result)
            assert render_response["status"] == "success", "Failed to render document"
            html_content = render_response["data"]["content"]

            # Step 5: Verify image appears in HTML
            assert len(html_content) > 100, "HTML content is too short"
            assert "<img" in html_content, "No <img> tag found in rendered HTML"
            assert (
                "Test graph visualization" in html_content or "alt=" in html_content
            ), "Image alt text not found in HTML"

            # Verify the image src attribute exists
            assert "src=" in html_content, "No image src attribute found"

            # For HTML format, images should be embedded as data URIs (not URL references)
            # This ensures offline viewing and proper PDF generation
            assert (
                "data:image" in html_content
            ), "Image not embedded as data URI in HTML (should download and embed for HTML/PDF)"

            # If embedding failed, verify URL fallback is present
            if "data:image" not in html_content:
                assert (
                    image_url in html_content
                ), "Neither embedded data URI nor URL reference found in HTML"

            # Verify image title is present
            assert "Test Graph" in html_content, "Image title not found in HTML"

            logger.info("✓ Image successfully rendered in HTML document with embedded data URI")


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_image_fragment_appears_in_rendered_pdf(logger, mcp_headers, image_server):
    """Verify that an added image fragment is included in PDF rendering.

    This test ensures that images make it through the full rendering pipeline
    including PDF generation via WeasyPrint.
    """
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Step 1: Create a document session
            create_result = await session.call_tool(
                "create_document_session",
                arguments={"template_id": "basic_report", "alias": "test_image_rendering-13"},
            )
            create_response = _parse_json_response(create_result)
            assert create_response["status"] == "success"
            session_id = create_response["data"]["session_id"]

            # Step 2: Set global parameters
            params_result = await session.call_tool(
                "set_global_parameters",
                arguments={
                    "session_id": session_id,
                    "parameters": {
                        "title": "PDF Image Test",
                        "author": "Test Suite",
                    },
                },
            )
            params_response = _parse_json_response(params_result)
            assert params_response["status"] == "success"

            # Step 3: Add an image fragment
            image_url = image_server.get_url("graph.png")
            add_image_result = await session.call_tool(
                "add_image_fragment",
                arguments={
                    "session_id": session_id,
                    "image_url": image_url,
                    "title": "Test Graph for PDF",
                    "width": 400,
                    "alt_text": "PDF test image",
                    "require_https": False,
                },
            )
            add_image_response = _parse_json_response(add_image_result)
            assert add_image_response["status"] == "success"

            # Step 4: Render document to PDF
            render_result = await session.call_tool(
                "get_document",
                arguments={
                    "session_id": session_id,
                    "format": "pdf",
                },
            )
            render_response = _parse_json_response(render_result)
            assert render_response["status"] == "success", "Failed to render PDF"
            pdf_base64 = render_response["data"]["content"]

            # Step 5: Verify PDF is valid and contains embedded image
            assert len(pdf_base64) > 1000, "PDF content is too short"

            # Decode base64 to verify it's actual PDF data
            pdf_bytes = base64.b64decode(pdf_base64)
            assert pdf_bytes.startswith(b"%PDF"), "Content is not a valid PDF file"

            # Parse PDF with pypdf to validate structure
            pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))

            # Validate PDF structure
            assert len(pdf_reader.pages) > 0, "PDF has no pages"
            num_pages = len(pdf_reader.pages)
            logger.info(f"PDF has {num_pages} page(s)")

            # Verify PDF metadata
            metadata = pdf_reader.metadata
            if metadata:
                logger.info(f"PDF metadata: {metadata}")

            # Check first page for content
            first_page = pdf_reader.pages[0]
            page_text = first_page.extract_text()

            # Verify document title appears in the PDF
            assert (
                "PDF Image Test" in page_text or "Test Suite" in page_text
            ), f"Expected document title not found in PDF text: {page_text[:200]}"

            # Verify PDF contains embedded images
            # Images are stored in page resources as XObjects
            has_images = False
            image_count = 0

            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    # Try to access page resources and XObjects
                    resources = page.get("/Resources")
                    if resources:
                        xobjects = resources.get("/XObject")
                        if xobjects:
                            # XObject is a dictionary-like object containing images
                            if hasattr(xobjects, "get_object"):
                                xobjects = xobjects.get_object()

                            # Iterate through XObjects looking for images
                            for obj_name in xobjects:
                                obj = xobjects[obj_name]
                                if hasattr(obj, "get_object"):
                                    obj = obj.get_object()

                                # Check if this XObject is an image
                                subtype = obj.get("/Subtype")
                                if subtype and str(subtype) == "/Image":
                                    has_images = True
                                    image_count += 1
                                    img_width = obj.get("/Width", "unknown")
                                    img_height = obj.get("/Height", "unknown")
                                    logger.info(
                                        f"Found embedded image #{image_count} on page {page_num + 1}: "
                                        f"{obj_name} ({img_width}x{img_height})"
                                    )
                except Exception as e:
                    logger.warning(f"Error checking page {page_num + 1} for images: {e}")

            assert has_images, "PDF does not contain any embedded images"
            logger.info(f"Total embedded images found: {image_count}")

            # PDF should be significantly larger with embedded image data
            assert (
                len(pdf_bytes) > 5000
            ), f"PDF is too small ({len(pdf_bytes)} bytes), likely malformed or missing embedded image"

            logger.info(
                f"✓ PDF validation complete: {len(pdf_bytes)} bytes, "
                f"{num_pages} page(s), embedded images verified"
            )


@pytest.mark.asyncio
@skip_if_mcp_unavailable
async def test_multiple_images_in_document(logger, mcp_headers, image_server):
    """Verify that multiple image fragments can be added and all appear in rendering."""
    async with streamablehttp_client(MCP_URL, headers=mcp_headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Create session
            create_result = await session.call_tool(
                "create_document_session",
                arguments={"template_id": "basic_report", "alias": "test_image_rendering-14"},
            )
            create_response = _parse_json_response(create_result)
            session_id = create_response["data"]["session_id"]

            # Set parameters
            await session.call_tool(
                "set_global_parameters",
                arguments={
                    "session_id": session_id,
                    "parameters": {"title": "Multi-Image Test", "author": "Test"},
                },
            )

            # Add first image
            image_url_1 = image_server.get_url("graph.png")
            result1 = await session.call_tool(
                "add_image_fragment",
                arguments={
                    "session_id": session_id,
                    "image_url": image_url_1,
                    "title": "First Graph",
                    "alt_text": "First test image",
                    "require_https": False,
                },
            )
            response1 = _parse_json_response(result1)
            assert response1["status"] == "success"

            # Add second image (same file, different title)
            result2 = await session.call_tool(
                "add_image_fragment",
                arguments={
                    "session_id": session_id,
                    "image_url": image_url_1,
                    "title": "Second Graph",
                    "alt_text": "Second test image",
                    "require_https": False,
                },
            )
            response2 = _parse_json_response(result2)
            assert response2["status"] == "success"

            # Render to HTML
            render_result = await session.call_tool(
                "get_document",
                arguments={"session_id": session_id, "format": "html"},
            )
            render_response = _parse_json_response(render_result)
            html_content = render_response["data"]["content"]

            # Verify both images appear in HTML
            img_count = html_content.count("<img")
            assert img_count >= 2, f"Expected at least 2 <img> tags, found {img_count}"

            # Verify both alt texts appear
            assert "First test image" in html_content, "First image alt text not found"
            assert "Second test image" in html_content, "Second image alt text not found"

            logger.info(f"✓ Multiple images rendered successfully ({img_count} images)")
