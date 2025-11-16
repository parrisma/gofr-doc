#!/usr/bin/env python3
"""Test proxy mode document rendering.

Tests the proxy=true parameter in get_document which stores rendered
documents on the server and returns a GUID for later retrieval instead
of the full document content.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import tempfile
import shutil

from app.sessions.manager import SessionManager
from app.sessions.storage import SessionStore
from app.templates.registry import TemplateRegistry
from app.rendering.engine import RenderingEngine
from app.styles.registry import StyleRegistry
from app.logger import session_logger
from app.validation.document_models import OutputFormat


@pytest.fixture
def temp_sessions_dir():
    """Create temporary sessions directory."""
    temp_dir = tempfile.mkdtemp(prefix="doco_proxy_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_proxy_dir():
    """Create temporary proxy storage directory."""
    temp_dir = tempfile.mkdtemp(prefix="doco_proxy_storage_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_templates_dir():
    """Use test templates directory."""
    return str(Path(__file__).parent.parent / "render" / "data" / "docs" / "templates")


@pytest.fixture
def temp_styles_dir():
    """Use test styles directory."""
    return str(Path(__file__).parent.parent / "render" / "data" / "docs" / "styles")


@pytest.fixture
def session_manager(temp_sessions_dir, temp_templates_dir):
    """Create SessionManager instance."""
    store = SessionStore(base_dir=temp_sessions_dir, logger=session_logger)
    registry = TemplateRegistry(templates_dir=temp_templates_dir, logger=session_logger)
    return SessionManager(
        session_store=store,
        template_registry=registry,
        logger=session_logger,
    )


@pytest.fixture
def rendering_engine(temp_templates_dir, temp_styles_dir, temp_proxy_dir):
    """Create RenderingEngine with proxy storage."""
    template_registry = TemplateRegistry(templates_dir=temp_templates_dir, logger=session_logger)
    style_registry = StyleRegistry(
        styles_dir=temp_styles_dir, group="public", logger=session_logger
    )
    return RenderingEngine(
        template_registry=template_registry,
        style_registry=style_registry,
        logger=session_logger,
        proxy_dir=temp_proxy_dir,
    )


# ============================================================================
# Proxy Rendering Tests
# ============================================================================


@pytest.mark.asyncio
async def test_render_with_proxy_returns_guid(session_manager, rendering_engine):
    """Test that proxy=true returns a GUID instead of document content."""
    # Create and populate session
    result = await session_manager.create_session(template_id="basic_report", group="public")
    session_id = result.session_id

    # Set required parameters
    await session_manager.set_global_parameters(
        session_id, {"title": "Proxy Test", "author": "Test User"}
    )

    # Add a fragment
    await session_manager.add_fragment(
        session_id=session_id,
        fragment_id="paragraph",
        parameters={"text": "This is test content"},
    )

    # Get session for rendering
    session = await session_manager.get_session(session_id)

    # Render with proxy=True
    output = await rendering_engine.render_document(
        session=session,
        output_format=OutputFormat.HTML,
        proxy=True,
    )

    # Verify proxy_guid is returned and content is empty
    assert output.proxy_guid is not None, "proxy_guid should be set"
    assert output.content == "", "content should be empty in proxy mode"
    assert len(output.proxy_guid) > 0, "proxy_guid should not be empty"


@pytest.mark.asyncio
async def test_proxy_document_can_be_retrieved(session_manager, rendering_engine):
    """Test that a proxy document can be retrieved by GUID."""
    # Create and populate session
    result = await session_manager.create_session(template_id="basic_report", group="public")
    session_id = result.session_id

    await session_manager.set_global_parameters(
        session_id, {"title": "Proxy Retrieval Test", "author": "Test"}
    )

    await session_manager.add_fragment(
        session_id=session_id,
        fragment_id="paragraph",
        parameters={"text": "Retrievable content"},
    )

    session = await session_manager.get_session(session_id)

    # Render with proxy and get the GUID
    output = await rendering_engine.render_document(
        session=session,
        output_format=OutputFormat.HTML,
        proxy=True,
    )

    proxy_guid = output.proxy_guid

    # Retrieve the proxy document
    retrieved = await rendering_engine.get_proxy_document(proxy_guid, "public")

    # Verify retrieved document
    assert retrieved.proxy_guid == proxy_guid
    assert retrieved.format == OutputFormat.HTML
    assert len(retrieved.content) > 0, "Retrieved content should not be empty"
    assert "Retrievable content" in retrieved.content, "Content should contain the fragment"


@pytest.mark.asyncio
async def test_proxy_mode_works_with_pdf(session_manager, rendering_engine):
    """Test proxy mode with PDF format."""
    result = await session_manager.create_session(template_id="basic_report", group="public")
    session_id = result.session_id

    await session_manager.set_global_parameters(
        session_id, {"title": "PDF Proxy Test", "author": "Test"}
    )

    await session_manager.add_fragment(
        session_id=session_id,
        fragment_id="paragraph",
        parameters={"text": "PDF content"},
    )

    session = await session_manager.get_session(session_id)

    # Render PDF with proxy
    output = await rendering_engine.render_document(
        session=session,
        output_format=OutputFormat.PDF,
        proxy=True,
    )

    assert output.proxy_guid is not None
    assert output.format == OutputFormat.PDF

    # Retrieve PDF proxy document
    retrieved = await rendering_engine.get_proxy_document(output.proxy_guid, "public")
    assert retrieved.format == OutputFormat.PDF
    assert len(retrieved.content) > 0, "PDF content should be base64-encoded"


@pytest.mark.asyncio
async def test_proxy_document_not_found_error(rendering_engine):
    """Test error handling for non-existent proxy documents."""
    with pytest.raises(ValueError, match="not found"):
        await rendering_engine.get_proxy_document("nonexistent-guid", "public")


@pytest.mark.asyncio
async def test_regular_rendering_still_works(session_manager, rendering_engine):
    """Test that non-proxy rendering still works normally."""
    result = await session_manager.create_session(template_id="basic_report", group="public")
    session_id = result.session_id

    await session_manager.set_global_parameters(
        session_id, {"title": "Regular Test", "author": "Test"}
    )

    await session_manager.add_fragment(
        session_id=session_id,
        fragment_id="paragraph",
        parameters={"text": "Regular content"},
    )

    session = await session_manager.get_session(session_id)

    # Render without proxy (proxy=False by default)
    output = await rendering_engine.render_document(
        session=session,
        output_format=OutputFormat.HTML,
        proxy=False,
    )

    # Verify content is returned and no proxy_guid
    assert output.proxy_guid is None or output.proxy_guid == "", "proxy_guid should not be set"
    assert len(output.content) > 0, "content should not be empty"
    assert "Regular content" in output.content


@pytest.mark.asyncio
async def test_proxy_documents_segregated_by_group(session_manager, rendering_engine):
    """Test that proxy documents are segregated by group."""
    # Create session in "public" group
    result1 = await session_manager.create_session(template_id="basic_report", group="public")
    session_id1 = result1.session_id

    await session_manager.set_global_parameters(
        session_id1, {"title": "Public Doc", "author": "Test"}
    )

    await session_manager.add_fragment(
        session_id=session_id1,
        fragment_id="paragraph",
        parameters={"text": "Public content"},
    )

    session1 = await session_manager.get_session(session_id1)

    # Render public document in proxy mode
    output1 = await rendering_engine.render_document(
        session=session1,
        output_format=OutputFormat.HTML,
        proxy=True,
    )

    guid1 = output1.proxy_guid

    # Verify document can be retrieved from public group
    retrieved1 = await rendering_engine.get_proxy_document(guid1, "public")
    assert retrieved1.proxy_guid == guid1
    assert "Public content" in retrieved1.content

    # Verify document NOT found in wrong group
    with pytest.raises(ValueError, match="not found"):
        await rendering_engine.get_proxy_document(guid1, "private")


@pytest.mark.asyncio
async def test_multiple_proxy_documents_independent(session_manager, rendering_engine):
    """Test that multiple proxy documents can be stored and retrieved independently."""
    # Create and render first document
    result1 = await session_manager.create_session(template_id="basic_report", group="public")
    session_id1 = result1.session_id

    await session_manager.set_global_parameters(session_id1, {"title": "Doc 1", "author": "Test"})

    await session_manager.add_fragment(
        session_id=session_id1,
        fragment_id="paragraph",
        parameters={"text": "Content 1"},
    )

    session1 = await session_manager.get_session(session_id1)
    output1 = await rendering_engine.render_document(
        session=session1,
        output_format=OutputFormat.HTML,
        proxy=True,
    )

    guid1 = output1.proxy_guid

    # Create and render second document
    result2 = await session_manager.create_session(template_id="basic_report", group="public")
    session_id2 = result2.session_id

    await session_manager.set_global_parameters(session_id2, {"title": "Doc 2", "author": "Test"})

    await session_manager.add_fragment(
        session_id=session_id2,
        fragment_id="paragraph",
        parameters={"text": "Content 2"},
    )

    session2 = await session_manager.get_session(session_id2)
    output2 = await rendering_engine.render_document(
        session=session2,
        output_format=OutputFormat.HTML,
        proxy=True,
    )

    guid2 = output2.proxy_guid

    # Verify both documents exist and have correct content
    retrieved1 = await rendering_engine.get_proxy_document(guid1, "public")
    retrieved2 = await rendering_engine.get_proxy_document(guid2, "public")

    assert "Content 1" in retrieved1.content
    assert "Content 2" in retrieved2.content
    assert guid1 != guid2
