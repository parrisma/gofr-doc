# Document Generation Guide

> **Related Documentation:**
> - [← Back to README](../README.md#core-documentation) | [Project Spec](PROJECT_SPEC.md) | [Development Guide](DEVELOPMENT.md)
> - **Features**: [Features Guide](FEATURES.md)
> - **Deployment**: [Docker](DOCKER.md) | [Authentication](AUTHENTICATION.md) | [Data Persistence](DATA_PERSISTENCE.md)
> - **Integration**: [Integration Guide](INTEGRATIONS.md)

This guide explains the document generation workflow, API surface, and best practices for using doco.

## Overview

doco implements a **stateful, discoverable document generation service** via MCP. The workflow follows:

1. **Discover** templates, fragments, and styles
2. **Create** a document session
3. **Iterate** by setting parameters and adding fragments
4. **Render** in multiple formats (HTML, PDF, Markdown)
5. **Cleanup** by aborting the session

## Key Concepts

### Templates

Templates define document structure and parameter schemas using:
- **YAML metadata** (`template.yaml`): Template ID, name, description, global parameters
- **Jinja2 template** (`document.html.jinja2`): HTML template injecting globals and fragments
- **Fragments**: Reusable content blocks with their own parameters

**Example template structure:**

```text
templates/
└── basic_report/
    ├── template.yaml              # Metadata & parameter schemas
    ├── document.html.jinja2        # Main document template
    └── fragments/
        ├── paragraph.html.jinja2   # Fragment templates
        └── section.html.jinja2
```

### Fragments

Fragments are modular content blocks inserted into documents. Each fragment:
- Has a unique `fragment_id` (e.g., `paragraph`, `section`)
- Accepts typed parameters defined in the template schema
- Generates a `fragment_instance_guid` (UUID4) when added to a session
- Can be positioned: `start`, `end`, `before:<guid>`, or `after:<guid>`
- Can be listed and removed at any time

### Sessions

A session represents an active document assembly. Sessions:
- Are created with a template ID
- Accept global parameters (applied to entire document)
- Accumulate fragments in order
- Persist across server restarts
- Are cleaned up with `abort_document_session`

### Styles

Styles are decoupled CSS bundles applied uniformly to all output formats. Each style:
- Has a unique `style_id` (e.g., `default`, `minimal`)
- Contains `style.yaml` (metadata) and `style.css` (complete stylesheet)
- Is optional during render (defaults to first loaded style)

## Tool Reference

### Discovery Tools

#### `list_templates`
List all registered document templates.

**Request:**
```json
{}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "templates": [
      {
        "template_id": "basic_report",
        "name": "Basic Report",
        "description": "Simple report with sections and paragraphs"
      }
    ]
  }
}
```

---

#### `get_template_details`
Fetch metadata and parameter schema for a template.

**Request:**
```json
{
  "template_id": "basic_report",
  "token": "optional_bearer_token"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "template_id": "basic_report",
    "name": "Basic Report",
    "description": "...",
    "global_parameters": [
      {
        "name": "title",
        "type": "string",
        "description": "Document title",
        "required": true
      }
    ]
  }
}
```

---

#### `list_template_fragments`
List fragment definitions available within a template.

**Request:**
```json
{
  "template_id": "basic_report",
  "token": "optional_bearer_token"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "template_id": "basic_report",
    "fragments": [
      {
        "fragment_id": "paragraph",
        "name": "Paragraph",
        "description": "A paragraph of text",
        "parameter_count": 1
      }
    ]
  }
}
```

---

#### `get_fragment_details`
Retrieve parameter schema for a specific fragment.

**Request:**
```json
{
  "template_id": "basic_report",
  "fragment_id": "paragraph",
  "token": "optional_bearer_token"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "template_id": "basic_report",
    "fragment_id": "paragraph",
    "name": "Paragraph",
    "description": "A paragraph of text",
    "parameters": [
      {
        "name": "text",
        "type": "string",
        "description": "Paragraph content",
        "required": true
      }
    ]
  }
}
```

---

#### `list_styles`
List all available rendering styles.

**Request:**
```json
{}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "styles": [
      {
        "style_id": "default",
        "name": "Default Style",
        "description": "Standard professional styling"
      }
    ]
  }
}
```

---

### Session Management Tools

#### `create_document_session`
Create a new document session for the specified template.

**Request:**
```json
{
  "template_id": "basic_report",
  "token": "optional_bearer_token"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "template_id": "basic_report",
    "created_at": "2025-11-15T10:30:00Z"
  }
}
```

---

#### `set_global_parameters`
Set or update global parameters for a document session. **Required before rendering.**

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "parameters": {
    "title": "Q4 2025 Report",
    "author": "Data Team"
  },
  "token": "optional_bearer_token"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "parameters": {
      "title": "Q4 2025 Report",
      "author": "Data Team"
    },
    "updated_at": "2025-11-15T10:31:00Z"
  }
}
```

---

### Fragment Management Tools

#### `add_fragment`
Add a fragment instance to the document body.

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "fragment_id": "paragraph",
  "parameters": {
    "text": "This is the introduction section."
  },
  "position": "end",
  "token": "optional_bearer_token"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "fragment_instance_guid": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "fragment_id": "paragraph",
    "position_index": 0,
    "message": "Fragment added successfully"
  }
}
```

---

#### `list_session_fragments`
List the ordered fragments currently in a session.

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "token": "optional_bearer_token"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "fragments": [
      {
        "fragment_instance_guid": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "fragment_id": "paragraph",
        "position_index": 0,
        "created_at": "2025-11-15T10:31:30Z"
      }
    ]
  }
}
```

---

#### `remove_fragment`
Remove a fragment instance from a session.

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "fragment_instance_guid": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "token": "optional_bearer_token"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "fragment_instance_guid": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "message": "Fragment removed successfully"
  }
}
```

---

### Rendering Tools

#### `get_document`
Render the document for a session in the requested format. **Requires prior `set_global_parameters`.**

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "format": "pdf",
  "style_id": "default",
  "token": "optional_bearer_token"
}
```

**Response (for PDF):**
```json
{
  "status": "success",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "format": "pdf",
    "style_id": "default",
    "content_base64": "JVBERi0xLjQK...",
    "media_type": "application/pdf",
    "size_bytes": 12345
  }
}
```

**Response (for HTML/Markdown):**
```json
{
  "status": "success",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "format": "html",
    "style_id": "default",
    "content": "<!DOCTYPE html>...",
    "media_type": "text/html",
    "size_bytes": 5678
  }
}
```

---

### Cleanup Tools

#### `abort_document_session`
Abort a session and delete its persisted data.

**Request:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "token": "optional_bearer_token"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "Session aborted and cleaned up"
  }
}
```

---

## Example Workflows

### Complete Document Generation Flow

```python
# 1. Discover templates
list_templates() → ["basic_report", "technical_doc"]

# 2. Get template details
get_template_details("basic_report")
→ global params: [title, author], output_format

# 3. Create session
create_document_session("basic_report")
→ session_id: "550e8400..."

# 4. Set global parameters (REQUIRED before render)
set_global_parameters(
  session_id="550e8400...",
  parameters={"title": "Q4 Report", "author": "Data Team"}
)

# 5. Discover fragments
list_template_fragments("basic_report")
→ fragments: [paragraph, section, chart]

# 6. Get fragment details
get_fragment_details("basic_report", "paragraph")
→ parameters: [text]

# 7. Add fragments in sequence
frag1_guid = add_fragment(
  session_id="550e8400...",
  fragment_id="paragraph",
  parameters={"text": "Introduction..."}
)
→ fragment_instance_guid: "f47ac10b..."

section_guid = add_fragment(
  session_id="550e8400...",
  fragment_id="section",
  parameters={"heading": "Analysis"},
  position="end"
)
→ fragment_instance_guid: "d4f1b3a0..."

# 8. List fragments (inspect state)
list_session_fragments("550e8400...")
→ [paragraph (index 0), section (index 1)]

# 9. Render in multiple formats
html_doc = get_document(
  session_id="550e8400...",
  format="html"
)

pdf_doc = get_document(
  session_id="550e8400...",
  format="pdf",
  style_id="minimal"
)

md_doc = get_document(
  session_id="550e8400...",
  format="md"
)

# 10. Clean up
abort_document_session("550e8400...")
```

### Iterative Refinement

Sessions support re-rendering and fragment adjustments:

```python
# After initial render, add more fragments
add_fragment(..., fragment_id="chart", ...)
add_fragment(..., fragment_id="conclusion", ...)

# Re-render with new content
pdf_v2 = get_document(session_id="...", format="pdf")

# Remove a fragment and re-render
remove_fragment(session_id="...", fragment_instance_guid="...")
pdf_v3 = get_document(session_id="...", format="pdf")
```

## Error Handling

All MCP responses follow a consistent error format:

```json
{
  "status": "error",
  "error_code": "SESSION_NOT_FOUND",
  "message": "Session '550e8400...' could not be retrieved.",
  "recovery_strategy": "Create a new session or verify the session identifier before retrying.",
  "details": {}
}
```

### Common Error Codes

| Code | Condition | Recovery |
|------|-----------|----------|
| `TEMPLATE_NOT_FOUND` | Template ID doesn't exist | Call `list_templates` to verify ID |
| `FRAGMENT_NOT_FOUND` | Fragment doesn't exist in template | Call `list_template_fragments` |
| `SESSION_NOT_FOUND` | Session ID doesn't exist | Create a new session |
| `SESSION_NOT_READY` | Global parameters not set before render | Call `set_global_parameters` |
| `INVALID_ARGUMENTS` | Pydantic validation failed | Check schema via `get_template_details` |
| `AUTH_REQUIRED` | Token required but not provided | Include valid JWT in `token` field |
| `AUTH_FAILED` | Token validation failed | Obtain a new token |
| `RENDER_FAILED` | Document rendering error | Check style ID, format, and session data |

## Best Practices

1. **Discover before creating**: Always call `list_templates` and `get_template_details` first
2. **Set parameters early**: Call `set_global_parameters` immediately after session creation
3. **Inspect fragments**: Use `list_session_fragments` to verify state before rendering
4. **Handle errors gracefully**: Check `recovery_strategy` in error responses
5. **Clean up sessions**: Always call `abort_document_session` when done
6. **Retry rendering**: Sessions remain valid for multiple renders; reuse to avoid re-assembly

## See Also

- [PROJECT_SPEC.md](../PROJECT_SPEC.md) — Technical specification
- [DATA_PERSISTENCE.md](DATA_PERSISTENCE.md) — Session storage and recovery
- [AUTHENTICATION.md](AUTHENTICATION.md) — JWT token management
