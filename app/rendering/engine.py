"""Rendering engine for document generation."""
from typing import Optional
import html2text
from weasyprint import HTML, CSS
from io import BytesIO
import base64

from app.validation.document_models import (
    DocumentSession,
    OutputFormat,
    GetDocumentOutput,
)
from app.templates.registry import TemplateRegistry
from app.styles.registry import StyleRegistry
from app.logger.interface import Logger


class RenderingEngine:
    """Handles document rendering to HTML, PDF, and Markdown."""

    def __init__(
        self,
        template_registry: TemplateRegistry,
        style_registry: StyleRegistry,
        logger: Logger,
    ):
        """
        Initialize the rendering engine.

        Args:
            template_registry: Template registry for Jinja2 templates
            style_registry: Style registry for CSS
            logger: Logger instance
        """
        self.template_registry = template_registry
        self.style_registry = style_registry
        self.logger = logger

    async def render_document(
        self,
        session: DocumentSession,
        output_format: OutputFormat,
        style_id: Optional[str] = None,
    ) -> GetDocumentOutput:
        """
        Render a document session to the specified format.

        Args:
            session: Document session to render
            output_format: Desired output format (HTML, PDF, MD)
            style_id: Style to apply (uses default if None)

        Returns:
            GetDocumentOutput with rendered content

        Raises:
            ValueError: If style not found or rendering fails
        """
        # Determine style
        if style_id is None:
            style_id = self.style_registry.get_default_style_id()
            if style_id is None:
                raise ValueError("No styles available")

        if not self.style_registry.style_exists(style_id):
            raise ValueError(f"Style '{style_id}' not found")

        # Generate HTML
        html_content = await self._render_html(session, style_id)

        # Convert to requested format
        if output_format == OutputFormat.HTML:
            content = html_content
        elif output_format == OutputFormat.PDF:
            content = await self._html_to_pdf(html_content, style_id)
        elif output_format == OutputFormat.MD:
            content = await self._html_to_markdown(html_content)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        self.logger.info(
            f"Rendered session {session.session_id} to {output_format.value} "
            f"with style {style_id}"
        )

        return GetDocumentOutput(
            session_id=session.session_id,
            format=output_format,
            style_id=style_id,
            content=content,
            message=f"Document rendered successfully as {output_format.value}",
        )

    async def _render_html(self, session: DocumentSession, style_id: str) -> str:
        """
        Render session to HTML using Jinja2 templates.

        Args:
            session: Document session
            style_id: Style to apply

        Returns:
            HTML string
        """
        # Get main document template
        template = self.template_registry.get_jinja_template(
            session.template_id, "document.html.jinja2"
        )

        # Get style CSS
        css_content = self.style_registry.get_style_css(style_id)

        # Render fragments
        rendered_fragments = []
        for fragment_instance in session.fragments:
            fragment_html = await self._render_fragment(
                session.template_id, fragment_instance.fragment_id, fragment_instance.parameters
            )
            rendered_fragments.append(fragment_html)

        # Render main document
        html_content = template.render(
            global_params=session.global_parameters or {},
            fragments=rendered_fragments,
            css=css_content,
        )

        return html_content

    async def _render_fragment(
        self, template_id: str, fragment_id: str, parameters: dict
    ) -> str:
        """
        Render a single fragment to HTML.

        Args:
            template_id: Template containing the fragment
            fragment_id: Fragment type
            parameters: Fragment parameters

        Returns:
            HTML string
        """
        # Get fragment template
        fragment_template = self.template_registry.get_jinja_template(
            template_id, f"fragments/{fragment_id}.html.jinja2"
        )

        # Render fragment
        fragment_html = fragment_template.render(**parameters)
        return fragment_html

    async def _html_to_pdf(self, html_content: str, style_id: str) -> str:
        """
        Convert HTML to PDF using WeasyPrint.

        Args:
            html_content: HTML content
            style_id: Style ID (for logging)

        Returns:
            Base64-encoded PDF content
        """
        try:
            # Create PDF in memory
            pdf_bytes = BytesIO()
            HTML(string=html_content).write_pdf(pdf_bytes)
            pdf_bytes.seek(0)

            # Encode as base64 for text transmission
            pdf_base64 = base64.b64encode(pdf_bytes.read()).decode("utf-8")

            self.logger.info(f"Converted HTML to PDF (style: {style_id})")
            return pdf_base64

        except Exception as e:
            self.logger.error(f"PDF conversion failed: {e}")
            raise ValueError(f"Failed to convert HTML to PDF: {e}")

    async def _html_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML to Markdown using html2text.

        Args:
            html_content: HTML content

        Returns:
            Markdown string
        """
        try:
            # Configure html2text
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            h.ignore_emphasis = False
            h.body_width = 0  # Don't wrap lines

            markdown_content = h.handle(html_content)

            self.logger.info("Converted HTML to Markdown")
            return markdown_content

        except Exception as e:
            self.logger.error(f"Markdown conversion failed: {e}")
            raise ValueError(f"Failed to convert HTML to Markdown: {e}")
