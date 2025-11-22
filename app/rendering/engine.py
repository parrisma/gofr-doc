"""Rendering engine for document generation."""

from typing import Optional
from datetime import datetime
import html2text
from weasyprint import HTML
from io import BytesIO
import base64
import uuid

from app.validation.document_models import (
    DocumentSession,
    OutputFormat,
    GetDocumentOutput,
    GetProxyDocumentOutput,
    FragmentInstance,
)
from app.templates.registry import TemplateRegistry
from app.styles.registry import StyleRegistry
from app.logger.interface import Logger
from app.config import get_default_proxy_dir


class RenderingEngine:
    """Handles document rendering to HTML, PDF, and Markdown."""

    def __init__(
        self,
        template_registry: TemplateRegistry,
        style_registry: StyleRegistry,
        logger: Logger,
        proxy_dir: Optional[str] = None,
    ):
        """
        Initialize the rendering engine.

        Args:
            template_registry: Template registry for Jinja2 templates
            style_registry: Style registry for CSS
            logger: Logger instance
            proxy_dir: Directory for proxy-stored documents (uses default if None)
        """
        self.template_registry = template_registry
        self.style_registry = style_registry
        self.logger = logger
        self.proxy_dir = proxy_dir or get_default_proxy_dir()

    async def render_document(
        self,
        session: DocumentSession,
        output_format: OutputFormat,
        style_id: Optional[str] = None,
        proxy: bool = False,
    ) -> GetDocumentOutput:
        """
        Render a document session to the specified format.

        Args:
            session: Document session to render
            output_format: Desired output format (HTML, PDF, MD)
            style_id: Style to apply (uses default if None)
            proxy: If True, store rendered document and return proxy_guid instead of content

        Returns:
            GetDocumentOutput with rendered content (or proxy_guid if proxy=True)

        Raises:
            ValueError: If style not found or rendering fails
        """
        # Determine style
        # Note: StyleRegistry is initialized with session.group,
        # so style_exists/get_default_style_id operate within that group
        if style_id is None:
            style_id = self.style_registry.get_default_style_id()
            if style_id is None:
                raise ValueError(f"No styles available in group '{session.group}'")

        if not self.style_registry.style_exists(style_id):
            raise ValueError(f"Style '{style_id}' not found in group '{session.group}'")

        # Generate HTML
        html_content = await self._render_html(session, style_id)

        # Convert to requested format
        if output_format == OutputFormat.HTML:
            content = html_content
        elif output_format == OutputFormat.PDF:
            content = await self._html_to_pdf(html_content, style_id)
        elif output_format == OutputFormat.MD:
            content = await self._html_to_markdown(html_content, session)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        self.logger.info(
            f"Rendered session {session.session_id} to {output_format.value} "
            f"with style {style_id}"
        )

        # Handle proxy storage if requested
        proxy_guid = None
        if proxy:
            proxy_guid = await self._store_proxy_document(content, session.group, output_format)
            # Return empty content with proxy_guid instead
            content = ""

        return GetDocumentOutput(
            session_id=session.session_id,
            format=output_format,
            style_id=style_id,
            content=content,
            message=f"Document rendered successfully as {output_format.value}",
            proxy_guid=proxy_guid,
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
            if isinstance(fragment_instance, FragmentInstance):
                fragment_html = await self._render_fragment(
                    session.template_id, fragment_instance.fragment_id, fragment_instance.parameters
                )
                # Wrap in dict to match template expectations (template expects fragment.html)
                rendered_fragments.append({"html": fragment_html})

        # Render main document
        html_content = template.render(
            global_params=session.global_parameters or {},
            fragments=rendered_fragments,
            css=css_content,
        )

        return html_content

    async def _render_fragment(self, template_id: str, fragment_id: str, parameters: dict) -> str:
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

        # Ensure parameters is a dict
        if parameters is None:
            parameters = {}

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

    async def _html_to_markdown(
        self, html_content: str, session: Optional[DocumentSession] = None
    ) -> str:
        """
        Convert HTML to Markdown using html2text.
        Enhances markdown tables with proper alignment markers based on fragment metadata.

        Args:
            html_content: HTML content
            session: Document session (optional, for table alignment enhancement)

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
            h.pad_tables = True  # Better formatted tables

            markdown_content = h.handle(html_content)

            # Enhance table alignment if session provided
            if session:
                markdown_content = self._enhance_markdown_tables(markdown_content, session)

            self.logger.info("Converted HTML to Markdown")
            return markdown_content

        except Exception as e:
            self.logger.error(f"Markdown conversion failed: {e}")
            raise ValueError(f"Failed to convert HTML to Markdown: {e}")

    def _enhance_markdown_tables(self, markdown: str, session: DocumentSession) -> str:
        """
        Post-process markdown to add alignment markers to tables.

        Markdown doesn't support colors/highlighting, so we only enhance alignment.
        Table fragments with column_alignments will get proper :---, :---:, ---: markers.

        Args:
            markdown: Markdown content with tables
            session: Document session with fragment metadata

        Returns:
            Enhanced markdown with alignment markers
        """
        import re

        # Extract table fragments with alignments
        # FragmentInstance doesn't have fragment_type, so we detect tables by column_alignments
        table_alignments = []
        for fragment in session.fragments:
            params = fragment.parameters or {}
            alignments = params.get("column_alignments")
            if alignments and isinstance(alignments, list):
                table_alignments.append(alignments)

        if not table_alignments:
            return markdown  # No tables with alignment info

        # Split markdown into lines
        lines = markdown.split("\n")
        enhanced_lines = []
        table_idx = 0

        i = 0
        while i < len(lines):
            line = lines[i]

            # Detect markdown table separator line (e.g., ---|---|---)
            if re.match(r"^\s*\|?\s*[-:]+\s*(\|\s*[-:]+\s*)+\|?\s*$", line):
                # This is a table separator
                if table_idx < len(table_alignments):
                    # Count columns from separator
                    col_count = line.count("|") - 1 if "|" in line else line.count("-")

                    # Get alignment for this table
                    alignments = table_alignments[table_idx]

                    # Build new separator with alignment markers
                    markers = []
                    for col_idx in range(col_count):
                        align = alignments[col_idx] if col_idx < len(alignments) else "left"
                        if align == "center":
                            markers.append(":---:")
                        elif align == "right":
                            markers.append("---:")
                        else:  # left or default
                            markers.append(":---")

                    # Replace separator line
                    enhanced_lines.append("| " + " | ".join(markers) + " |")
                    table_idx += 1
                else:
                    enhanced_lines.append(line)
            else:
                enhanced_lines.append(line)

            i += 1

        return "\n".join(enhanced_lines)

    async def _store_proxy_document(
        self, content: str, group: str, output_format: OutputFormat
    ) -> str:
        """
        Store a rendered document in proxy storage.

        Args:
            content: Document content (base64 for PDF, text for HTML/MD)
            group: Group to organize proxy documents
            output_format: Format of the document

        Returns:
            GUID for retrieving the document later
        """
        from pathlib import Path
        import json

        # Create group directory
        group_dir = Path(self.proxy_dir) / group
        group_dir.mkdir(parents=True, exist_ok=True)

        # Generate GUID
        proxy_guid = str(uuid.uuid4())

        # Create proxy metadata and file
        proxy_file = group_dir / f"{proxy_guid}.json"
        proxy_data = {
            "proxy_guid": proxy_guid,
            "format": (
                output_format.value if isinstance(output_format, OutputFormat) else output_format
            ),
            "content": content,
            "group": group,  # Store group ownership for verification on retrieval
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        try:
            with proxy_file.open("w", encoding="utf-8") as f:
                json.dump(proxy_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Stored proxy document {proxy_guid} in group {group}")
            return proxy_guid

        except Exception as e:
            self.logger.error(f"Failed to store proxy document: {e}")
            raise ValueError(f"Failed to store proxy document: {e}")

    async def get_proxy_document(self, proxy_guid: str) -> GetProxyDocumentOutput:
        """
        Retrieve a previously stored proxy document.

        Args:
            proxy_guid: GUID of the proxy document

        Returns:
            GetProxyDocumentOutput with document content and stored group

        Raises:
            ValueError: If document not found
        """
        from pathlib import Path
        import json

        # Search all group directories for the proxy document
        proxy_dir_path = Path(self.proxy_dir)
        found_file = None

        for group_dir in proxy_dir_path.iterdir():
            if group_dir.is_dir():
                candidate_file = group_dir / f"{proxy_guid}.json"
                if candidate_file.exists():
                    found_file = candidate_file
                    break

        if not found_file:
            raise ValueError(f"Proxy document '{proxy_guid}' not found")

        try:
            with found_file.open("r", encoding="utf-8") as f:
                proxy_data = json.load(f)

            stored_group = proxy_data.get("group")
            if not stored_group:
                raise ValueError(f"Proxy document '{proxy_guid}' missing group metadata")

            self.logger.info(f"Retrieved proxy document {proxy_guid} from group {stored_group}")

            return GetProxyDocumentOutput(
                proxy_guid=proxy_guid,
                format=OutputFormat(proxy_data["format"]),
                content=proxy_data["content"],
                group=stored_group,  # Include stored group for verification
                message="Proxy document retrieved successfully",
            )

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse proxy document: {e}")
            raise ValueError(f"Proxy document is corrupted: {e}")
        except Exception as e:
            self.logger.error(f"Failed to retrieve proxy document: {e}")
            raise ValueError(f"Failed to retrieve proxy document: {e}")
