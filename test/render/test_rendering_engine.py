"""Unit tests for RenderingEngine without MCP/Web server dependencies.
Tests use real implementations of logger, WeasyPrint, and html2text
to verify actual output conversions.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import base64
from unittest.mock import Mock

from app.validation.document_models import (
    DocumentSession,
    OutputFormat,
)
from app.logger import ConsoleLogger
from jinja2 import Template

from app.rendering.engine import RenderingEngine


@pytest.fixture
def console_logger():
    """Create a real ConsoleLogger instance."""
    return ConsoleLogger()


@pytest.fixture
def mock_template_registry():
    """Create a mock TemplateRegistry."""
    registry = Mock()

    # Mock document template
    doc_template = Template(
        """<html>
<head><style>{{ css }}</style></head>
<body>
<h1>{{ global_params.get('title', 'Untitled') }}</h1>
{% for fragment in fragments %}
<div class="fragment">{{ fragment }}</div>
{% endfor %}
</body>
</html>"""
    )

    # Mock fragment templates
    paragraph_template = Template("<p>{% if text %}{{ text }}{% endif %}</p>")
    section_template = Template("<section><h2>{{ heading }}</h2><div>{{ content }}</div></section>")

    def get_jinja_template(template_id, template_name):
        if template_name == "document.html.jinja2":
            return doc_template
        elif "paragraph" in template_name:
            return paragraph_template
        elif "section" in template_name:
            return section_template
        raise ValueError(f"Template not found: {template_name}")

    registry.get_jinja_template = get_jinja_template
    return registry


@pytest.fixture
def mock_style_registry():
    """Create a mock StyleRegistry."""
    registry = Mock()
    registry.get_default_style_id.return_value = "default"
    registry.style_exists.return_value = True
    registry.get_style_css.return_value = "body { font-family: Arial; }"
    return registry


@pytest.fixture
async def rendering_engine(mock_template_registry, mock_style_registry, console_logger):
    """Create a RenderingEngine instance with mocked registries."""
    return RenderingEngine(
        template_registry=mock_template_registry,
        style_registry=mock_style_registry,
        logger=console_logger,
    )


# Test Classes:


class TestRenderingEngineInitialization:
    """Test engine initialization."""

    def test_init_with_valid_registries(
        self, mock_template_registry, mock_style_registry, console_logger
    ):
        """Test initialization with valid registries."""
        engine = RenderingEngine(
            template_registry=mock_template_registry,
            style_registry=mock_style_registry,
            logger=console_logger,
        )
        assert engine is not None
        assert engine.template_registry == mock_template_registry
        assert engine.style_registry == mock_style_registry
        assert engine.logger == console_logger

    def test_init_stores_registries_and_logger(
        self, mock_template_registry, mock_style_registry, console_logger
    ):
        """Test that registries and logger are properly stored."""
        engine = RenderingEngine(
            template_registry=mock_template_registry,
            style_registry=mock_style_registry,
            logger=console_logger,
        )
        assert hasattr(engine, "template_registry")
        assert hasattr(engine, "style_registry")
        assert hasattr(engine, "logger")


class TestRenderDocumentToHTML:
    """Test rendering to HTML format with real output."""

    @pytest.mark.asyncio
    async def test_render_document_html_returns_valid_html_string(self, rendering_engine):
        """Test that HTML render returns a valid HTML string."""
        session = DocumentSession(
            session_id="test-1",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test Report"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.HTML)
        assert output.format == OutputFormat.HTML
        assert isinstance(output.content, str)
        assert len(output.content) > 0

    @pytest.mark.asyncio
    async def test_render_document_html_contains_css(self, rendering_engine):
        """Test that HTML output contains CSS."""
        session = DocumentSession(
            session_id="test-2",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.HTML)
        assert "font-family: Arial" in output.content

    @pytest.mark.asyncio
    async def test_render_document_html_contains_rendered_fragments(self, rendering_engine):
        """Test that HTML output contains rendered fragments."""
        session = DocumentSession(
            session_id="test-3",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[{"fragment_id": "paragraph", "parameters": {"text": "Hello World"}}],  # type: ignore[arg-type] - test uses simplified dict
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.HTML)
        assert "Hello World" in output.content

    @pytest.mark.asyncio
    async def test_render_document_html_with_default_style(self, rendering_engine):
        """Test HTML rendering with default style."""
        session = DocumentSession(
            session_id="test-4",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.HTML)
        assert output.style_id == "default"

    @pytest.mark.asyncio
    async def test_render_document_html_with_custom_style(self, rendering_engine):
        """Test HTML rendering with custom style."""
        session = DocumentSession(
            session_id="test-5",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(
            session, OutputFormat.HTML, style_id="custom"
        )
        assert output.style_id == "custom"

    @pytest.mark.asyncio
    async def test_render_document_html_structure_validity(self, rendering_engine):
        """Test that HTML output has valid structure."""
        session = DocumentSession(
            session_id="test-6",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test Report"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.HTML)
        html = output.content
        assert html.count("<html") >= 1
        assert html.count("</html>") >= 1
        assert "<head>" in html
        assert "</head>" in html


class TestRenderDocumentToPDF:
    """Test PDF rendering with WeasyPrint (real conversion)."""

    @pytest.mark.asyncio
    async def test_render_document_pdf_returns_base64_encoded_string(self, rendering_engine):
        """Test that PDF render returns base64-encoded string."""
        session = DocumentSession(
            session_id="test-7",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.PDF)
        assert output.format == OutputFormat.PDF
        assert isinstance(output.content, str)
        assert len(output.content) > 0

    @pytest.mark.asyncio
    async def test_render_document_pdf_base64_is_valid(self, rendering_engine):
        """Test that PDF content is valid base64."""
        session = DocumentSession(
            session_id="test-8",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.PDF)
        # Should not raise an exception
        decoded = base64.b64decode(output.content)
        assert len(decoded) > 0

    @pytest.mark.asyncio
    async def test_render_document_pdf_can_be_decoded(self, rendering_engine):
        """Test that PDF base64 can be decoded to bytes."""
        session = DocumentSession(
            session_id="test-9",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.PDF)
        decoded_bytes = base64.b64decode(output.content)
        assert isinstance(decoded_bytes, bytes)

    @pytest.mark.asyncio
    async def test_render_document_pdf_content_is_actual_pdf(self, rendering_engine):
        """Test that decoded PDF content is actual PDF format."""
        session = DocumentSession(
            session_id="test-10",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.PDF)
        decoded_bytes = base64.b64decode(output.content)
        # PDF files start with %PDF
        assert decoded_bytes.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_pdf_output_format_specification(self, rendering_engine):
        """Test PDF output format specification."""
        session = DocumentSession(
            session_id="test-11",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.PDF)
        assert output.format == OutputFormat.PDF
        assert output.session_id == "test-11"


class TestRenderDocumentToMarkdown:
    """Test Markdown rendering with html2text (real conversion)."""

    @pytest.mark.asyncio
    async def test_render_document_markdown_returns_string(self, rendering_engine):
        """Test that Markdown render returns a string."""
        session = DocumentSession(
            session_id="test-12",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.MD)
        assert output.format == OutputFormat.MD
        assert isinstance(output.content, str)
        assert len(output.content) > 0

    @pytest.mark.asyncio
    async def test_render_document_markdown_valid_structure(self, rendering_engine):
        """Test Markdown output has valid structure."""
        session = DocumentSession(
            session_id="test-13",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test Report"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.MD)
        markdown = output.content
        assert "Test Report" in markdown

    @pytest.mark.asyncio
    async def test_html_to_markdown_converts_headings(self, rendering_engine):
        """Test that HTML headings are converted to Markdown."""
        session = DocumentSession(
            session_id="test-14",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "My Heading"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.MD)
        markdown = output.content
        # html2text converts <h1> to markdown heading format
        assert "My Heading" in markdown

    @pytest.mark.asyncio
    async def test_render_fragment(self, rendering_engine):
        """Test individual fragment rendering."""
        rendered = await rendering_engine._render_fragment(
            "basic_report", "paragraph", {"text": "Test paragraph"}
        )
        assert "Test paragraph" in rendered
        assert "<p>" in rendered


class TestOutputFormatValidation:
    """Test output format conversion and validation."""

    @pytest.mark.asyncio
    async def test_html_format_output_structure(self, rendering_engine):
        """Test HTML format output structure."""
        session = DocumentSession(
            session_id="test-15",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.HTML)
        assert output.format == OutputFormat.HTML
        assert output.session_id == "test-15"
        assert output.style_id is not None

    @pytest.mark.asyncio
    async def test_pdf_format_output_structure(self, rendering_engine):
        """Test PDF format output structure."""
        session = DocumentSession(
            session_id="test-16",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.PDF)
        assert output.format == OutputFormat.PDF
        assert output.session_id == "test-16"
        assert output.style_id is not None

    @pytest.mark.asyncio
    async def test_markdown_format_output_structure(self, rendering_engine):
        """Test Markdown format output structure."""
        session = DocumentSession(
            session_id="test-17",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        output = await rendering_engine.render_document(session, OutputFormat.MD)
        assert output.format == OutputFormat.MD
        assert output.session_id == "test-17"
        assert output.style_id is not None

    @pytest.mark.asyncio
    async def test_all_formats_contain_correct_format_field(self, rendering_engine):
        """Test all formats return correct format field."""
        session = DocumentSession(
            session_id="test-18",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        for output_format in [OutputFormat.HTML, OutputFormat.PDF, OutputFormat.MD]:
            output = await rendering_engine.render_document(session, output_format)
            assert output.format == output_format

    @pytest.mark.asyncio
    async def test_all_formats_contain_session_id(self, rendering_engine):
        """Test all formats contain session ID."""
        session = DocumentSession(
            session_id="test-19",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        for output_format in [OutputFormat.HTML, OutputFormat.PDF, OutputFormat.MD]:
            output = await rendering_engine.render_document(session, output_format)
            assert output.session_id == "test-19"

    @pytest.mark.asyncio
    async def test_all_formats_contain_success_message(self, rendering_engine):
        """Test all formats contain success message."""
        session = DocumentSession(
            session_id="test-20",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        for output_format in [OutputFormat.HTML, OutputFormat.PDF, OutputFormat.MD]:
            output = await rendering_engine.render_document(session, output_format)
            assert "successfully" in output.message.lower()


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_raises_valueerror_on_missing_style(
        self, mock_template_registry, mock_style_registry, console_logger
    ):
        """Test error on missing style."""
        mock_style_registry.get_default_style_id.return_value = None
        engine = RenderingEngine(
            template_registry=mock_template_registry,
            style_registry=mock_style_registry,
            logger=console_logger,
        )

        session = DocumentSession(
            session_id="test-21",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        with pytest.raises(ValueError):
            await engine.render_document(session, OutputFormat.HTML)

    @pytest.mark.asyncio
    async def test_raises_valueerror_on_invalid_style_id(
        self, mock_template_registry, mock_style_registry, console_logger
    ):
        """Test error on invalid style ID."""
        mock_style_registry.style_exists.return_value = False
        engine = RenderingEngine(
            template_registry=mock_template_registry,
            style_registry=mock_style_registry,
            logger=console_logger,
        )

        session = DocumentSession(
            session_id="test-22",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        with pytest.raises(ValueError):
            await engine.render_document(session, OutputFormat.HTML, style_id="invalid")

    @pytest.mark.asyncio
    async def test_raises_valueerror_on_unsupported_format(self, rendering_engine):
        """Test error on unsupported format."""
        session = DocumentSession(
            session_id="test-23",
            template_id="basic_report",
            group="public",
            global_parameters={"title": "Test"},
            fragments=[],
            created_at="2025-11-16T00:00:00",
            updated_at="2025-11-16T00:00:00",
        )

        # Create an invalid format
        invalid_format = "INVALID"
        with pytest.raises(ValueError):
            await rendering_engine.render_document(session, invalid_format)
