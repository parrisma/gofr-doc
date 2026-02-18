"""MCP tool schemas (list_tools) for the document service.

This module isolates the very large Tool(...) schema definitions from the MCP
server entrypoint to improve navigability.

Behavior must remain identical to the legacy schemas previously defined in
app/mcp_server/mcp_server.py.
"""

from __future__ import annotations

from typing import List

from mcp.types import Tool


async def build_tools() -> List[Tool]:
    return [
        Tool(
            name="ping",
            description=(
                "Health check - Verify service availability. "
                "WORKFLOW: Use this first to confirm the service is responsive before making other requests. "
                "Returns server status and current timestamp."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="help",
            description=(
                "Comprehensive Documentation - Get complete workflow guidance, GUID lifecycle rules, common pitfalls, "
                "and a step-by-step authoring guide for creating your own templates, fragments, and styles. "
                "WORKFLOW: Call this anytime you need help understanding the service workflow or troubleshooting issues. "
                "Returns: Service overview, GUID persistence rules (when session_ids and fragment_instance_guids are created/deleted), "
                "common mistakes to avoid, example workflows, tool sequencing guide, and content authoring reference. "
                "CRITICAL TOPICS COVERED: How long GUIDs persist, when to save them, workflow best practices, parameter requirements, "
                "how to create new templates/fragments/styles with correct YAML schemas and directory layout. "
                "USE THIS: When starting a new task, when confused about workflow, when encountering repeated errors, "
                "or when you need to create custom templates or fragments."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_session_status",
            description=(
                "Session Inspection - Get current state of a document session including readiness for rendering. "
                "WORKFLOW: Use this to verify a session exists and check its current state before performing operations. "
                "Returns: session_id, template_id, has_global_parameters (bool), fragment_count, is_ready_to_render (bool), timestamps. "
                "USEFUL FOR: Verifying old session_ids still exist, checking if globals are set, seeing fragment count before rendering. "
                "ERROR RECOVERY: If you get 'session not found' errors, call this first to verify the session_id is valid. "
                "GROUP SECURITY: Can only access sessions from your authenticated group. Returns 'SESSION_NOT_FOUND' for sessions in other groups. "
                "AUTHENTICATION: Requires JWT Bearer token. Generic errors prevent information leakage about sessions in other groups."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
                    },
                    "token": {"type": "string", "description": "Optional bearer token."},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="list_active_sessions",
            description=(
                "Session Discovery - List all available document sessions with summary information including their friendly aliases. "
                "WORKFLOW: Use this to see all existing sessions, discover session aliases, recover lost session identifiers, or check session states. "
                "Returns: Array of session summaries with session_id, alias (friendly name), template_id, fragment_count, has_global_parameters, timestamps. "
                "ALIASES: Each session has a friendly alias (e.g., 'invoice-march', 'weekly-report') that's easier to remember than UUIDs. "
                "Use the alias in other tools - they accept either session_id (UUID) or alias for identification. "
                "USEFUL FOR: Finding a session alias you forgot, discovering available sessions by name, seeing all in-progress documents, understanding session state. "
                "RECOVERY: If you lost a session identifier, call this to find both the UUID and friendly alias. "
                "GROUP ISOLATION: Only returns sessions from your authenticated group. You will NOT see sessions created by other groups. "
                "AUTHENTICATION: Requires JWT Bearer token to determine which group's sessions to return."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="validate_parameters",
            description=(
                "Parameter Validation - Check if parameters are valid BEFORE saving them to avoid errors. "
                "WORKFLOW: Call this before set_global_parameters or add_fragment to catch mistakes early. "
                "Returns: is_valid (bool), detailed errors array with parameter names, expected types, received types, examples. "
                "USEFUL FOR: Pre-flight validation, understanding parameter requirements, debugging validation errors. "
                "PARAMETERS: Set parameter_type='global' for template globals, 'fragment' for fragment parameters. "
                "ERROR DETAILS: Each error includes parameter name, expected type, what you provided, and example values. "
                "\n"
                "TABLE FRAGMENT VALIDATION: When validating table parameters, common errors to check:\n"
                "- rows must be non-empty array of arrays with consistent column counts\n"
                "- column_widths total must not exceed 100% (e.g., {0: '40%', 1: '60%'} is valid, {0: '60%', 1: '50%'} fails)\n"
                "- column indices in number_format, highlight_columns, column_widths must be valid (0-based, less than column count)\n"
                "- row indices in highlight_rows must be valid (0-based, less than row count)\n"
                "- colors must be theme names ('primary', 'success', etc.) or valid hex codes ('#4A90E2')\n"
                "- sort_by column references must exist (column name if has_header=true, or valid column index)\n"
                "Use this tool to catch these before calling add_fragment!\n"
                "\n"
                "GROUP SECURITY: Validates against templates in your authenticated group. Returns 'TEMPLATE_NOT_FOUND' for templates in other groups. "
                "AUTHENTICATION: Requires JWT Bearer token for group-based template access."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "Template identifier to validate against.",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Parameters to validate (the actual values you want to check).",
                    },
                    "parameter_type": {
                        "type": "string",
                        "enum": ["global", "fragment"],
                        "description": "Type of parameters: 'global' for template globals, 'fragment' for fragment parameters.",
                        "default": "global",
                    },
                    "fragment_id": {
                        "type": "string",
                        "description": "Required when parameter_type='fragment'. Fragment identifier from list_template_fragments.",
                    },
                    "token": {"type": "string", "description": "Optional bearer token."},
                },
                "required": ["template_id", "parameters", "parameter_type"],
            },
        ),
        Tool(
            name="list_templates",
            description=(
                "Discovery - List all available document templates. "
                "WORKFLOW: Start here to discover which templates are available. Each template defines a document structure. "
                "Returns: Array of templates with template_id (use this in create_document_session), name, description, and group. "
                "NEXT STEPS: Use get_template_details to inspect a specific template's requirements. "
                "AUTHENTICATION: No authentication required - this is a discovery tool available to all clients."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_template_details",
            description=(
                "Discovery - Get detailed schema for a specific template including required global parameters. "
                "WORKFLOW: Call this after list_templates to understand what global parameters a template requires. "
                "Returns: Template metadata, list of global parameters with types and requirements, embedded fragment definitions. "
                "NEXT STEPS: Use create_document_session with the template_id, then set_global_parameters with the required params. "
                "ERROR HANDLING: If template_id not found, call list_templates to get valid identifiers."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "Template identifier from list_templates (e.g., 'basic_report', 'invoice').",
                    },
                    "token": {
                        "type": "string",
                        "description": "Optional bearer token for authenticated access.",
                    },
                },
                "required": ["template_id"],
            },
        ),
        Tool(
            name="list_template_fragments",
            description=(
                "Discovery - List all fragments available within a specific template. "
                "WORKFLOW: After selecting a template, call this to see what content fragments you can add to the document body. "
                "Returns: Array of fragments with fragment_id (use in add_fragment), name, description, and parameter_count. "
                "NEXT STEPS: Use get_fragment_details to see what parameters each fragment requires before calling add_fragment. "
                "ERROR HANDLING: If template_id not found, call list_templates first. "
                "\n"
                "NOTE: The 'table' fragment (if available in the template) is highly capable with 14 parameters supporting:\n"
                "financial formatting (currency/percent/decimal), theme colors, row/column highlighting, sorting, and precise column width control. "
                "Always call get_fragment_details for 'table' to see its full capabilities before use."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "Template identifier from list_templates.",
                    },
                    "token": {"type": "string", "description": "Optional bearer token."},
                },
                "required": ["template_id"],
            },
        ),
        Tool(
            name="get_fragment_details",
            description=(
                "Discovery - Get parameter schema for a specific fragment to understand what data it needs. "
                "WORKFLOW: Call this before add_fragment to discover required/optional parameters and their types. "
                "Returns: Fragment metadata, parameter definitions with types, defaults, examples, and validation rules. "
                "NEXT STEPS: Collect the required parameter values, then call add_fragment with the parameters object. "
                "ERROR HANDLING: If fragment_id not found, call list_template_fragments to see available fragments. "
                "\n"
                "IMPORTANT FOR TABLE FRAGMENTS: The 'table' fragment has 14 powerful parameters including:\n"
                "- Data structure (rows, has_header, title, width)\n"
                "- Layout control (column_alignments, column_widths with percentage-based sizing)\n"
                "- Visual styling (border_style, zebra_stripe, compact mode)\n"
                "- Number formatting (currency with any ISO code, percent, decimal precision, accounting notation)\n"
                "- Color theming (header_color, stripe_color, highlight_rows, highlight_columns - supports 8 theme colors + hex)\n"
                "- Data sorting (sort_by with single/multi-column support, numeric/string detection)\n"
                "Call this tool with fragment_id='table' to see detailed specifications for each parameter."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {"type": "string", "description": "Template identifier."},
                    "fragment_id": {
                        "type": "string",
                        "description": "Fragment identifier from list_template_fragments (e.g., 'heading', 'paragraph', 'table').",
                    },
                    "token": {"type": "string", "description": "Optional bearer token."},
                },
                "required": ["template_id", "fragment_id"],
            },
        ),
        Tool(
            name="list_styles",
            description=(
                "Discovery - List all available visual styles for document rendering. "
                "WORKFLOW: Optional - call this before get_document to see styling options. "
                "Returns: Array of styles with style_id (use in get_document), name, and description. "
                "NEXT STEPS: Use the style_id in get_document's style_id parameter to apply custom styling. "
                "DEFAULT: If not specified, the default style is automatically applied."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="create_document_session",
            description=(
                "Session Management - Create a new document session based on a template. This is REQUIRED before building content. "
                "WORKFLOW: After discovering templates with list_templates and understanding requirements with get_template_details, create a session. "
                "Returns: session_id (UUID), alias (friendly name), template_id, creation timestamps. "
                "NEXT STEPS: (1) Call set_global_parameters to set required template parameters, (2) Call add_fragment repeatedly to build document content, (3) Call get_document to render. "
                "ERROR HANDLING: If template_id not found, call list_templates to get valid identifiers. If alias already exists, choose a different name. "
                "IMPORTANT: Sessions persist across API calls - use either session_id (UUID) or alias in subsequent operations. Alias is easier for LLMs to remember. "
                "AUTHENTICATION: Requires JWT Bearer token. Session is bound to your group - you can only access sessions created by your group. "
                "GROUP ISOLATION: Sessions are isolated by group. Aliases are unique within a group but can be reused across groups."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "template_id": {
                        "type": "string",
                        "description": "Template identifier from list_templates. The template defines the document structure.",
                    },
                    "alias": {
                        "type": "string",
                        "description": "Friendly name for this session (3-64 chars: letters, numbers, hyphens, underscores). Example: 'q4-report-2025', 'marketing-draft'. Use this instead of UUID in subsequent calls.",
                    },
                    "token": {
                        "type": "string",
                        "description": "Optional bearer token for authenticated sessions.",
                    },
                },
                "required": ["template_id", "alias"],
            },
        ),
        Tool(
            name="set_global_parameters",
            description=(
                "Session Configuration - Set or update global parameters that apply to the entire document (e.g., title, author, date). "
                "WORKFLOW: Call this after create_document_session to configure template-wide settings. Can be called multiple times to update parameters. "
                "Returns: Updated session state with current global_parameters. "
                "NEXT STEPS: After setting globals, use add_fragment to build the document body content. "
                "ERROR HANDLING: If session_id not found, create a new session with create_document_session. "
                "TIP: Use get_template_details to see what global parameters are required for your template before calling this. "
                "GROUP SECURITY: Can only modify sessions from your authenticated group. Returns 'SESSION_NOT_FOUND' for cross-group access attempts. "
                "AUTHENTICATION: Requires JWT Bearer token for session ownership verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Dictionary of global parameter values. Keys match parameter names from template schema. Example: {'title': 'Q4 Report', 'author': 'John Doe', 'date': '2025-11-16'}",
                        "additionalProperties": True,
                    },
                    "token": {
                        "type": "string",
                        "description": "Bearer token if session requires authentication.",
                    },
                },
                "required": ["session_id", "parameters"],
            },
        ),
        Tool(
            name="add_fragment",
            description=(
                "Content Building - Add a content fragment (e.g., heading, paragraph, table) to the document body. Call repeatedly to build up content. "
                "WORKFLOW: After create_document_session and set_global_parameters, call this to add each piece of content. Fragments are added in order. "
                "Returns: fragment_instance_guid (unique ID for this specific fragment instance - save it to remove or reorder later), position confirmation. "
                "NEXT STEPS: Continue calling add_fragment for additional content. When done, call get_document to render the final output. "
                "ERROR HANDLING: If fragment_id not found, call list_template_fragments. If parameters invalid, call get_fragment_details to see requirements. "
                "TIP: Use get_fragment_details first to understand what parameters each fragment type requires. "
                "\n\n"
                "TABLE FRAGMENT GUIDE: The 'table' fragment supports 14 parameters for rich tabular data:\n"
                "- REQUIRED: rows (array of arrays) - e.g., [['Name', 'Age'], ['Alice', '30']]\n"
                "- STRUCTURE: has_header (bool), title (string), width ('auto'|'full'|'80%')\n"
                "- LAYOUT: column_alignments (array: ['left', 'center', 'right']), column_widths (dict: {0: '40%', 1: '60%'} - must total <=100%)\n"
                "- STYLING: border_style ('full'|'horizontal'|'minimal'|'none'), zebra_stripe (bool), compact (bool)\n"
                "- FORMATTING: number_format (dict: {1: 'currency:USD', 2: 'percent'}) - supports currency:CODE, percent, decimal:N, integer, accounting\n"
                "- COLORS: header_color, stripe_color (theme: 'primary'|'success'|'warning'|'danger'|'info'|'light'|'dark'|'muted' OR hex: '#4A90E2')\n"
                "- HIGHLIGHTS: highlight_rows (dict: {0: 'success', 2: 'warning'}), highlight_columns (dict: {1: 'info'})\n"
                "- SORTING: sort_by (string column name | int column index | {column: 1, order: 'asc'|'desc'} | array for multi-column)\n"
                "\n"
                "EXAMPLE TABLE with all features:\n"
                "{'rows': [['Product','Q1','Q2','Q3'], ['Widget','1500','1800','2100'], ['Gadget','900','1200','1400']],\n"
                " 'has_header': True, 'title': 'Sales Report', 'width': 'full',\n"
                " 'column_alignments': ['left','right','right','right'], 'column_widths': {0: '40%', 1: '20%', 2: '20%', 3: '20%'},\n"
                " 'border_style': 'full', 'zebra_stripe': True, 'compact': False,\n"
                " 'number_format': {1: 'currency:USD', 2: 'currency:USD', 3: 'currency:USD'},\n"
                " 'header_color': 'primary', 'stripe_color': 'light', 'highlight_columns': {3: 'success'},\n"
                " 'sort_by': {'column': 3, 'order': 'desc'}}\n"
                "\n"
                "GROUP SECURITY: Can only add fragments to sessions from your authenticated group. Returns 'SESSION_NOT_FOUND' for cross-group access. "
                "AUTHENTICATION: Requires JWT Bearer token for session ownership verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
                    },
                    "fragment_id": {
                        "type": "string",
                        "description": "Fragment type from list_template_fragments (e.g., 'heading', 'paragraph', 'bullet_list', 'table').",
                    },
                    "parameters": {
                        "type": "object",
                        "description": (
                            "Fragment-specific parameters. Use get_fragment_details to see required fields. "
                            "Examples: "
                            "heading: {'text': 'Chapter 1', 'level': 1}, "
                            "paragraph: {'text': 'Content here', 'heading': 'Optional Section'}, "
                            "table: {'rows': [['A','B'],['1','2']], 'has_header': True, 'column_widths': {0: '60%', 1: '40%'}} - see tool description for full table capabilities. "
                            "NOTE: For images, use add_image_fragment tool instead of add_fragment - it provides immediate URL validation and format-specific rendering."
                        ),
                        "additionalProperties": True,
                    },
                    "position": {
                        "type": "string",
                        "description": "Where to insert: 'end' (default, append to bottom), 'start' (prepend to top), 'before:<guid>' (insert before fragment with guid), 'after:<guid>' (insert after fragment with guid).",
                    },
                    "token": {"type": "string", "description": "Bearer token if required."},
                },
                "required": ["session_id", "fragment_id", "parameters"],
            },
        ),
        Tool(
            name="add_image_fragment",
            description=(
                "Content Building - Add an image from a URL to the document with immediate URL validation. "
                "\n\n"
                "NOTE: CRITICAL: URL VALIDATION HAPPENS IMMEDIATELY (not at render time)\n"
                "When you call this tool, the service immediately validates:\n"
                "1. URL format and accessibility (HTTP HEAD request)\n"
                "2. Content-Type header matches allowed image types\n"
                "3. Image size within limits (default 10MB max)\n"
                "4. HTTPS protocol (unless require_https=false)\n"
                "\n"
                "WORKFLOW: After create_document_session, call this to add images. URL must be publicly accessible.\n"
                "\n"
                "PARAMETERS:\n"
                "- REQUIRED: image_url (string) - Must be accessible URL returning valid image content-type\n"
                "- OPTIONAL: title (string) - Caption displayed above image\n"
                "- OPTIONAL: width (integer, pixels) - If only width set, height scales proportionally\n"
                "- OPTIONAL: height (integer, pixels) - If only height set, width scales proportionally\n"
                "- OPTIONAL: alt_text (string) - Accessibility text (defaults to title or 'Image')\n"
                "- OPTIONAL: alignment ('left'|'center'|'right') - Default: 'center'\n"
                "- OPTIONAL: require_https (bool) - Default: true (enforces HTTPS for security)\n"
                "- OPTIONAL: position (string) - Where to insert: 'end' (default), 'start', 'before:<guid>', 'after:<guid>'\n"
                "\n"
                "ALLOWED IMAGE TYPES:\n"
                "[Y] image/png, image/jpeg, image/jpg, image/gif, image/webp, image/svg+xml\n"
                "[N] PDFs, HTML, text files, etc. will be rejected\n"
                "\n"
                "RENDERING BEHAVIOR:\n"
                "- PDF/HTML: Image downloaded and embedded as base64 (no external dependencies)\n"
                "- Markdown: Image linked via URL (![alt](url) syntax)\n"
                "\n"
                "COMMON ERROR CODES & FIXES:\n"
                "- INVALID_IMAGE_URL: Non-HTTPS URL with require_https=true -> Use HTTPS or set require_https=false\n"
                "- IMAGE_URL_NOT_ACCESSIBLE: HTTP 404/403/500 -> Verify URL in browser, check if public\n"
                "- INVALID_IMAGE_CONTENT_TYPE: URL returns non-image type -> Ensure URL points to actual image file\n"
                "- IMAGE_TOO_LARGE: File > 10MB -> Compress image or use smaller version\n"
                "- IMAGE_URL_TIMEOUT: Slow/unreachable server -> Check network, try different CDN\n"
                "\n"
                "EXAMPLE - Basic image:\n"
                "{'image_url': 'https://example.com/logo.png', 'title': 'Company Logo', 'alignment': 'center'}\n"
                "\n"
                "EXAMPLE - Sized image with alt text:\n"
                "{'image_url': 'https://cdn.example.com/chart.png', 'width': 800, 'alt_text': 'Q4 Sales Chart', 'alignment': 'center'}\n"
                "\n"
                "EXAMPLE - Allow HTTP (dev/testing only):\n"
                "{'image_url': 'http://localhost:8000/test.jpg', 'require_https': False, 'title': 'Test Image'}\n"
                "\n"
                "TIP: Test URLs in browser first to verify accessibility and content-type!\n"
                "\n"
                "Returns: fragment_instance_guid if successful, or detailed error with recovery guidance.\n"
                "GROUP SECURITY: Can only add images to sessions from your authenticated group. "
                "AUTHENTICATION: Requires JWT Bearer token for session ownership verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
                    },
                    "image_url": {
                        "type": "string",
                        "description": (
                            "URL of the image to download and display. VALIDATED IMMEDIATELY via HTTP HEAD request. "
                            "Requirements: (1) Publicly accessible, (2) Returns 200 OK, (3) Content-Type is image/*, (4) Size <=10MB. "
                            "Allowed types: image/png, image/jpeg, image/jpg, image/gif, image/webp, image/svg+xml. "
                            "Example: 'https://cdn.example.com/images/logo.png'. "
                            "TIP: Test URL in browser first to verify it loads and shows image content-type."
                        ),
                    },
                    "title": {
                        "type": "string",
                        "description": (
                            "Optional title/caption displayed above the image. "
                            "Rendered as bold text or caption depending on output format. "
                            "Example: 'Figure 1: Sales Trends 2024'"
                        ),
                    },
                    "width": {
                        "type": "integer",
                        "description": (
                            "Target width in pixels (positive integer). "
                            "If only width specified, height scales proportionally to maintain aspect ratio. "
                            "If both width and height specified, image may be stretched/squashed. "
                            "Example: 800 for 800px wide. Leave unset to use original image size."
                        ),
                    },
                    "height": {
                        "type": "integer",
                        "description": (
                            "Target height in pixels (positive integer). "
                            "If only height specified, width scales proportionally to maintain aspect ratio. "
                            "If both width and height specified, image may be stretched/squashed. "
                            "Example: 600 for 600px tall. Leave unset to use original image size."
                        ),
                    },
                    "alt_text": {
                        "type": "string",
                        "description": (
                            "Alternative text for accessibility (screen readers, image load failures). "
                            "Should describe the image content for users who can't see it. "
                            "If not provided, defaults to title parameter or 'Image'. "
                            "Example: 'Bar chart showing quarterly revenue growth from Q1 to Q4 2024'"
                        ),
                    },
                    "alignment": {
                        "type": "string",
                        "enum": ["left", "center", "right"],
                        "description": (
                            "Image horizontal alignment within the document. "
                            "'left': Align to left margin, 'center': Center in page (default), 'right': Align to right margin. "
                            "Default: 'center' if not specified."
                        ),
                    },
                    "require_https": {
                        "type": "boolean",
                        "description": (
                            "Security setting for URL protocol validation. "
                            "If true (default): Only HTTPS URLs accepted - rejects http:// URLs. "
                            "If false: Allows both HTTPS and HTTP URLs (use for development/testing only). "
                            "Default: true. IMPORTANT: Set to false only for local testing (http://localhost)."
                        ),
                    },
                    "position": {
                        "type": "string",
                        "description": "Where to insert: 'end' (default), 'start', 'before:<guid>', 'after:<guid>'.",
                    },
                    "token": {"type": "string", "description": "Bearer token if required."},
                },
                "required": ["session_id", "image_url"],
            },
        ),
        Tool(
            name="remove_fragment",
            description=(
                "Content Editing - Remove a specific fragment instance from the document. "
                "WORKFLOW: To remove content, use the fragment_instance_guid returned from add_fragment or found in list_session_fragments. "
                "Returns: Confirmation of removal with updated fragment count. "
                "NEXT STEPS: Continue editing with add_fragment or remove_fragment, then call get_document when ready. "
                "ERROR HANDLING: If guid not found, call list_session_fragments to see current fragments and their GUIDs. "
                "GROUP SECURITY: Can only remove fragments from sessions in your authenticated group. Returns 'SESSION_NOT_FOUND' for cross-group access. "
                "AUTHENTICATION: Requires JWT Bearer token for session ownership verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
                    },
                    "fragment_instance_guid": {
                        "type": "string",
                        "description": "Unique identifier for the specific fragment instance to remove (from add_fragment response or list_session_fragments).",
                    },
                    "token": {"type": "string", "description": "Bearer token if required."},
                },
                "required": ["session_id", "fragment_instance_guid"],
            },
        ),
        Tool(
            name="list_session_fragments",
            description=(
                "Session Inspection - List all fragments currently in the document in their display order. "
                "WORKFLOW: Call this to inspect the current document structure, get fragment GUIDs for removal, or verify your changes. "
                "Returns: Ordered array of fragments with guid (for remove_fragment), fragment_id, parameters, creation timestamp, and position. "
                "NEXT STEPS: Use the guid values with remove_fragment to delete content, or continue building with add_fragment. "
                "TIP: This shows the current state of your document before rendering. "
                "GROUP SECURITY: Can only list fragments from sessions in your authenticated group. Returns 'SESSION_NOT_FOUND' for cross-group access. "
                "AUTHENTICATION: Requires JWT Bearer token for session ownership verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
                    },
                    "token": {"type": "string", "description": "Bearer token if required."},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="abort_document_session",
            description=(
                "Session Cleanup - Permanently delete a session and all its data. Use this to clean up abandoned or test sessions. "
                "WORKFLOW: Call when you want to discard a document session and free up resources. "
                "Returns: Confirmation of deletion. "
                "WARNING: This is irreversible. All fragments and parameters in the session will be permanently deleted. "
                "ALTERNATIVE: If you just want to modify the document, use remove_fragment or set_global_parameters instead. "
                "GROUP SECURITY: Can only delete sessions from your authenticated group. Returns 'SESSION_NOT_FOUND' for cross-group access. "
                "AUTHENTICATION: Requires JWT Bearer token for session ownership verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
                    },
                    "token": {"type": "string", "description": "Bearer token if required."},
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="get_document",
            description=(
                "Final Rendering - Generate the finished document in your chosen format (HTML, PDF, or Markdown). "
                "WORKFLOW: After create_document_session, set_global_parameters, and adding fragments with add_fragment, call this to render. "
                "Returns: Rendered document content in requested format with metadata (format, session_id, render timestamp, success status). "
                "FORMATS: 'html' (web display), 'pdf' (printable, base64-encoded), 'md' or 'markdown' (plain text with markdown). "
                "STYLING: Optionally specify style_id from list_styles, or omit for default styling. "
                "PROXY MODE: Set proxy=true to store rendered document on server and receive proxy_guid + download_url instead of full content. "
                "  NOTE: IMPORTANT: proxy_guid is NOT the same as session_id! The proxy_guid is a unique identifier for the stored rendered document. "
                "  RESPONSE FIELDS: "
                "    - proxy_guid: Unique GUID for THIS rendered document (different from session_id) "
                "    - download_url: Complete HTTP URL to retrieve document: {web_server}/proxy/{proxy_guid} "
                "    - content: Will be null when proxy=true "
                "  RETRIEVAL: Use the download_url to GET the rendered document. The proxy_guid alone can also be used with /proxy/{proxy_guid} endpoint. "
                "  BENEFITS: Reduces network overhead for large documents (PDFs); persistent server-side storage for later retrieval. "
                "  EXAMPLE: get_document(session_id='abc-123', format='pdf', proxy=true) -> returns proxy_guid='xyz-789' and download_url='http://server:8012/proxy/xyz-789' "
                "ERROR HANDLING: If session not ready, verify global parameters are set and fragments added. If session_id not found, check the ID or create a new session. "
                "TIP: You can call this multiple times with different formats to get the same document in different outputs. "
                "GROUP SECURITY: Can only render documents from sessions in your authenticated group. Returns 'SESSION_NOT_FOUND' for cross-group access. "
                "AUTHENTICATION: Requires JWT Bearer token for session ownership verification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session identifier: Use the session alias (friendly name from create_document_session) OR the UUID. Aliases are easier to remember and use. Example alias: 'my-report-2025'. Example UUID: '12345678-1234-1234-1234-123456789abc'.",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["html", "pdf", "md"],
                        "description": "Output format: 'html' (web/display), 'pdf' (print-ready, base64), 'md' (markdown for text processing).",
                    },
                    "style_id": {
                        "type": "string",
                        "description": "Optional styling: style identifier from list_styles (e.g., 'light', 'dark', 'bizlight'). Omit for default styling.",
                    },
                    "proxy": {
                        "type": "boolean",
                        "description": "If true, store rendered document on server and return proxy_guid instead of content for later retrieval.",
                    },
                    "token": {"type": "string", "description": "Bearer token if required."},
                },
                "required": ["session_id", "format"],
            },
        ),
        # ====================================================================
        # Plot tools (migrated from gofr-plot)
        # ====================================================================
        Tool(
            name="render_graph",
            description=(
                "Render a graph visualization and return it as a base64-encoded image or storage GUID. "
                "\n\n**AUTHENTICATION**: Requires a valid JWT 'auth_token' parameter. "
                "\n\n**BASIC USAGE**: Provide 'title' (string) and at least one dataset (y1 array or legacy 'y' array). "
                "The 'x' parameter is optional - if omitted, indices [0, 1, 2, ...] are auto-generated. "
                "\n\n**MULTI-DATASET**: Supports up to 5 datasets (y1-y5) with optional labels (label1-label5) and colors (color1-color5). "
                "\n\n**CHART TYPES**: 'line' (default), 'scatter', or 'bar'. Use list_handlers tool to see descriptions. "
                "\n\n**THEMES**: 'light' (default), 'dark', 'bizlight', 'bizdark'. Use list_themes tool for details. "
                "\n\n**PROXY MODE**: Set proxy=true to save the image to persistent storage and receive a GUID instead of base64 data. "
                "Use get_image with the GUID to retrieve the image later. "
                "\n\n**OUTPUT FORMATS**: 'png' (default), 'jpg', 'svg', 'pdf'. "
                "\n\n**AXIS CONTROLS**: Optional parameters for axis limits (xmin/xmax/ymin/ymax) and custom tick positions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The title of the graph"},
                    "x": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "X-axis data points (optional, defaults to indices)",
                    },
                    "y": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Y-axis data (backward compat - maps to y1)",
                    },
                    "y1": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "First dataset Y-axis data (required unless 'y' provided)",
                    },
                    "y2": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Second dataset (optional)",
                    },
                    "y3": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Third dataset (optional)",
                    },
                    "y4": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Fourth dataset (optional)",
                    },
                    "y5": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Fifth dataset (optional)",
                    },
                    "label1": {"type": "string", "description": "Label for first dataset (legend)"},
                    "label2": {"type": "string", "description": "Label for second dataset"},
                    "label3": {"type": "string", "description": "Label for third dataset"},
                    "label4": {"type": "string", "description": "Label for fourth dataset"},
                    "label5": {"type": "string", "description": "Label for fifth dataset"},
                    "color1": {
                        "type": "string",
                        "description": "Color for first dataset (e.g., 'red', '#FF5733')",
                    },
                    "color2": {"type": "string", "description": "Color for second dataset"},
                    "color3": {"type": "string", "description": "Color for third dataset"},
                    "color4": {"type": "string", "description": "Color for fourth dataset"},
                    "color5": {"type": "string", "description": "Color for fifth dataset"},
                    "xlabel": {
                        "type": "string",
                        "description": "X-axis label (default: 'X-axis')",
                        "default": "X-axis",
                    },
                    "ylabel": {
                        "type": "string",
                        "description": "Y-axis label (default: 'Y-axis')",
                        "default": "Y-axis",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["line", "scatter", "bar"],
                        "description": "Chart type (default: 'line')",
                        "default": "line",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["png", "jpg", "svg", "pdf"],
                        "description": "Image format (default: 'png')",
                        "default": "png",
                    },
                    "proxy": {
                        "type": "boolean",
                        "description": "If true, save to storage and return GUID (default: false)",
                        "default": False,
                    },
                    "alias": {
                        "type": "string",
                        "description": "Friendly name for proxy mode (3-64 chars, alphanumeric with hyphens/underscores)",
                    },
                    "color": {
                        "type": "string",
                        "description": "Line/marker color (backward compat, maps to color1)",
                    },
                    "line_width": {
                        "type": "number",
                        "description": "Line width (default: 2.0)",
                        "default": 2.0,
                    },
                    "marker_size": {
                        "type": "number",
                        "description": "Marker size for scatter (default: 36.0)",
                        "default": 36.0,
                    },
                    "alpha": {
                        "type": "number",
                        "description": "Transparency 0.0-1.0 (default: 1.0)",
                        "default": 1.0,
                    },
                    "theme": {
                        "type": "string",
                        "enum": ["light", "dark", "bizlight", "bizdark"],
                        "description": "Visual theme (default: 'light')",
                        "default": "light",
                    },
                    "xmin": {"type": "number", "description": "Minimum x-axis value"},
                    "xmax": {"type": "number", "description": "Maximum x-axis value"},
                    "ymin": {"type": "number", "description": "Minimum y-axis value"},
                    "ymax": {"type": "number", "description": "Maximum y-axis value"},
                    "x_major_ticks": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Custom x-axis major tick positions",
                    },
                    "y_major_ticks": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Custom y-axis major tick positions",
                    },
                    "x_minor_ticks": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Custom x-axis minor tick positions",
                    },
                    "y_minor_ticks": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Custom y-axis minor tick positions",
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (preferred). Include your JWT token here.",
                    },
                    "token": {
                        "type": "string",
                        "description": "JWT authentication token (legacy backward compatibility).",
                    },
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="get_image",
            description=(
                "Retrieve a previously stored graph image using its GUID or alias. "
                "\n\n**AUTHENTICATION**: Requires a valid JWT 'auth_token' parameter. "
                "The token's group must match the group that created the image. "
                "\n\n**IDENTIFIERS**: Use either a GUID or alias set during render_graph. "
                "\n\n**OUTPUT**: Returns the image as base64-encoded data with metadata."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "Image GUID or alias"},
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (preferred).",
                    },
                    "token": {
                        "type": "string",
                        "description": "JWT authentication token (legacy backward compatibility).",
                    },
                },
                "required": ["identifier"],
            },
        ),
        Tool(
            name="list_images",
            description=(
                "List all stored plot images accessible to your token's group. "
                "\n\n**AUTHENTICATION**: Requires a valid JWT 'auth_token' parameter. "
                "Only images belonging to your token's group will be listed. "
                "\n\n**OUTPUT**: Returns GUIDs, aliases, and metadata for stored plot images."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (preferred).",
                    },
                    "token": {
                        "type": "string",
                        "description": "JWT authentication token (legacy backward compatibility).",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="list_themes",
            description=(
                "Discover all available visual themes with descriptions. "
                "\n\n**AUTHENTICATION**: NOT required. "
                "\n\n**PURPOSE**: Use before calling render_graph to choose a theme. "
                "Available themes: 'light', 'dark', 'bizlight', 'bizdark'."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="list_handlers",
            description=(
                "Discover all available chart types with capability descriptions. "
                "\n\n**AUTHENTICATION**: NOT required. "
                "\n\n**PURPOSE**: Use before calling render_graph to choose the right chart type. "
                "Available types: 'line', 'scatter', 'bar'."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="add_plot_fragment",
            description=(
                "Render a graph and embed it as a fragment in a document session. "
                "\n\n**AUTHENTICATION**: Requires a valid JWT 'auth_token' parameter. "
                "\n\n**TWO MODES**: "
                "1. GUID path: Provide 'plot_guid' to embed a previously rendered plot. "
                "2. Inline path: Provide render params (title, y1, etc.) to render and embed in one call. "
                "\n\n**WORKFLOW**: "
                "- GUID: render_graph(proxy=true) -> get plot_guid -> add_plot_fragment(session_id, plot_guid=<guid>) "
                "- Inline: add_plot_fragment(session_id, title='My Chart', y1=[1,2,3]) "
                "\n\n**IMAGE EMBEDDING**: The plot is embedded as a base64 data URI in the document. "
                "Rendered HTML/PDF documents are self-contained - no external server needed to view plots."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Document session GUID or alias",
                    },
                    "plot_guid": {
                        "type": "string",
                        "description": "GUID of previously rendered plot (from render_graph with proxy=true)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Graph title (required for inline render, optional caption for GUID path)",
                    },
                    "x": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "X-axis data (optional)",
                    },
                    "y1": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "First dataset (required for inline render)",
                    },
                    "y2": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Second dataset (optional)",
                    },
                    "y3": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Third dataset (optional)",
                    },
                    "y4": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Fourth dataset (optional)",
                    },
                    "y5": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Fifth dataset (optional)",
                    },
                    "label1": {"type": "string", "description": "Label for first dataset"},
                    "label2": {"type": "string", "description": "Label for second dataset"},
                    "label3": {"type": "string", "description": "Label for third dataset"},
                    "label4": {"type": "string", "description": "Label for fourth dataset"},
                    "label5": {"type": "string", "description": "Label for fifth dataset"},
                    "color1": {"type": "string", "description": "Color for first dataset"},
                    "color2": {"type": "string", "description": "Color for second dataset"},
                    "color3": {"type": "string", "description": "Color for third dataset"},
                    "color4": {"type": "string", "description": "Color for fourth dataset"},
                    "color5": {"type": "string", "description": "Color for fifth dataset"},
                    "xlabel": {"type": "string", "description": "X-axis label"},
                    "ylabel": {"type": "string", "description": "Y-axis label"},
                    "type": {
                        "type": "string",
                        "enum": ["line", "scatter", "bar"],
                        "description": "Chart type",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["png", "jpg", "svg", "pdf"],
                        "description": "Image format",
                    },
                    "theme": {
                        "type": "string",
                        "enum": ["light", "dark", "bizlight", "bizdark"],
                        "description": "Visual theme",
                    },
                    "width": {"type": "integer", "description": "Image width in pixels"},
                    "height": {"type": "integer", "description": "Image height in pixels"},
                    "alt_text": {"type": "string", "description": "Accessibility text"},
                    "alignment": {
                        "type": "string",
                        "enum": ["left", "center", "right"],
                        "description": "Image alignment (default: center)",
                    },
                    "position": {
                        "type": "string",
                        "description": "Fragment position: 'end', 'start', 'before:<guid>', 'after:<guid>'",
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (preferred).",
                    },
                    "token": {
                        "type": "string",
                        "description": "JWT authentication token (legacy backward compatibility).",
                    },
                },
                "required": ["session_id"],
            },
        ),
    ]
