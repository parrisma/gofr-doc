# Features Guide

> **Related Documentation:**
> - [← Back to README](../README.md#features-documentation) | [Document Generation](DOCUMENT_GENERATION.md) | [Project Spec](PROJECT_SPEC.md)
> - **Deployment**: [Docker](DOCKER.md) | [Authentication](AUTHENTICATION.md)
> - **Development**: [Development Guide](DEVELOPMENT.md) | [Data Persistence](DATA_PERSISTENCE.md)

## Overview

Doco provides powerful features for dynamic document generation:

- **[Tables](#tables)** - Rich formatted tables with styling and number formatting
- **[Images](#images)** - URL-based images with validation and format-specific rendering
- **[Groups](#groups)** - Multi-tenant resource organization and isolation
- **[Proxy Mode](#proxy-mode)** - Server-side document storage for large files

---

## Tables

Rich, formatted tables with support for styling, number formatting, and multiple output formats.

### Quick Start

#### Basic Table

```json
{
  "rows": [
    ["Name", "Age", "City"],
    ["Alice", "30", "New York"],
    ["Bob", "25", "Boston"]
  ],
  "has_header": true,
  "title": "Employee Directory"
}
```

#### Financial Table

```json
{
  "rows": [
    ["Quarter", "Revenue", "Growth"],
    ["Q1 2024", "1250000", "0.15"],
    ["Q2 2024", "1380000", "0.104"]
  ],
  "has_header": true,
  "title": "Quarterly Performance",
  "column_alignments": ["left", "right", "right"],
  "number_format": {
    "1": "currency:USD",
    "2": "percent"
  },
  "header_color": "primary",
  "zebra_stripe": true
}
```

### Table Parameters

#### Core Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `rows` | array of arrays | Yes | - | 2D array of table data |
| `has_header` | boolean | No | false | Treat first row as header |
| `title` | string | No | - | Table title/caption |
| `width` | string | No | "auto" | "auto", "full", or percentage |

#### Styling Parameters

| Parameter | Type | Options | Description |
|-----------|------|---------|-------------|
| `header_color` | string | primary, secondary, success, warning, danger, info, light, dark | Header row background color |
| `zebra_stripe` | boolean | - | Alternating row colors |
| `border_style` | string | solid, dashed, dotted, none | Border style |
| `column_alignments` | array | left, center, right | Per-column alignment |
| `column_widths` | array | percentages/pixels | Per-column width |

#### Number Formatting

Format numbers in specific columns:

```json
"number_format": {
  "1": "currency:USD",      // Column 1: $1,234.56
  "2": "percent",            // Column 2: 12.5%
  "3": "decimal:2"           // Column 3: 123.45
}
```

**Supported Formats:**
- `currency:CODE` - Currency (USD, EUR, GBP, JPY, etc.)
- `percent` - Percentage (12.5%)
- `decimal:N` - Decimal places (123.45)

#### Sorting

```json
"sort_by": {
  "column": "Revenue",      // Column name or index
  "order": "desc"            // "asc" or "desc"
}
```

#### Row/Column Highlighting

```json
"highlight_rows": [1, 3],   // Row indices (0-based after header)
"highlight_columns": [2],   // Column indices (0-based)
"highlight_color": "warning"
```

### Advanced Examples

#### Styled Financial Report

```json
{
  "rows": [
    ["Metric", "Q1", "Q2", "Q3", "Q4"],
    ["Revenue", "1250000", "1380000", "1520000", "1680000"],
    ["Expenses", "850000", "920000", "1010000", "1120000"],
    ["Profit", "400000", "460000", "510000", "560000"]
  ],
  "has_header": true,
  "title": "2024 Financial Summary",
  "width": "100%",
  "header_color": "primary",
  "zebra_stripe": true,
  "border_style": "solid",
  "column_alignments": ["left", "right", "right", "right", "right"],
  "number_format": {
    "1": "currency:USD",
    "2": "currency:USD",
    "3": "currency:USD",
    "4": "currency:USD"
  },
  "highlight_rows": [3],
  "highlight_color": "success"
}
```

#### Comparison Table with Sorting

```json
{
  "rows": [
    ["Product", "Price", "Rating", "Sales"],
    ["Widget Pro", "299.99", "4.5", "1250"],
    ["Gadget Plus", "199.99", "4.8", "2100"],
    ["Tool Master", "399.99", "4.2", "890"]
  ],
  "has_header": true,
  "title": "Product Comparison",
  "sort_by": {"column": "Sales", "order": "desc"},
  "number_format": {
    "1": "currency:USD",
    "2": "decimal:1"
  },
  "column_alignments": ["left", "right", "center", "right"],
  "header_color": "info",
  "zebra_stripe": true
}
```

### Output Format Support

Tables render appropriately for each format:

- **HTML**: Full styling with CSS classes
- **PDF**: Styled tables via weasyprint
- **Markdown**: Plain text tables with alignment

---

## Images

URL-based images with immediate validation and format-specific rendering.

### Quick Start

```json
{
  "session_id": "abc-123",
  "image_url": "https://example.com/chart.png",
  "title": "Q4 Performance Chart",
  "width": 600,
  "alignment": "center"
}
```

### Image Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `session_id` | string | Yes | - | Session identifier |
| `image_url` | string | Yes | - | Image URL (validated immediately) |
| `title` | string | No | - | Caption above image |
| `width` | integer | No | - | Target width in pixels |
| `height` | integer | No | - | Target height in pixels |
| `alt_text` | string | No | title or "Image" | Accessibility text |
| `alignment` | string | No | center | left, center, right |
| `require_https` | boolean | No | true | Require HTTPS URLs |
| `position` | string | No | end | end, start, before:<guid>, after:<guid> |

### URL Validation

Images are validated **immediately when added** (not at render time):

1. **Scheme validation** - Check HTTPS (or HTTP if allowed)
2. **URL format** - Validate well-formed URL
3. **HEAD request** - Verify URL is accessible
4. **Content-Type** - Check valid image type
5. **Size check** - Reject images over limit

**Allowed Content-Types:**
- `image/png`
- `image/jpeg`
- `image/jpg`
- `image/gif`
- `image/webp`
- `image/svg+xml`

### Error Handling

```json
{
  "status": "error",
  "error_code": "INVALID_IMAGE_URL",
  "message": "Image URL must use HTTPS protocol",
  "recovery": "Use HTTPS URL or set require_https=false",
  "details": {
    "url": "http://example.com/image.png",
    "reason": "Non-HTTPS URL with require_https=true"
  }
}
```

### Format-Specific Rendering

**PDF/HTML**: Images are embedded (base64 or downloaded)
**Markdown**: Images are linked with markdown syntax

### Examples

#### Simple Image

```json
{
  "session_id": "abc-123",
  "image_url": "https://example.com/logo.png",
  "title": "Company Logo",
  "alignment": "center"
}
```

#### Sized Image with HTTP Allowed

```json
{
  "session_id": "abc-123",
  "image_url": "http://internal.local/chart.png",
  "title": "Internal Dashboard",
  "width": 800,
  "height": 600,
  "require_https": false,
  "alt_text": "Performance dashboard showing metrics"
}
```

#### Positioned Image

```json
{
  "session_id": "abc-123",
  "image_url": "https://example.com/diagram.png",
  "position": "after:fragment-guid-123",
  "alignment": "right"
}
```

---

## Groups

Multi-tenant resource organization with directory-based isolation.

### Overview

Groups provide logical organization of templates, fragments, and styles:

- **Organize Resources** - Group related items (e.g., "public", "research", "internal")
- **Isolate Access** - Prevent cross-group references
- **Filter Resources** - Query by group via CLI and API
- **Track Metadata** - Know which group owns each resource

Every resource belongs to exactly one group.

### Directory Structure

```
templates/
  ├── public/
  │   ├── basic_report/
  │   └── monthly_summary/
  └── research/
      └── research_paper/

fragments/
  ├── public/
  │   └── news_item/
  └── internal/
      └── employee_bio/

styles/
  ├── public/
  │   └── default/
  └── corporate/
      └── branded/
```

### Resource Metadata

Every resource declares its group:

```yaml
metadata:
  name: "Basic Report"
  description: "A simple report"
  version: "1.0"
  group: "public"  # Must match directory
```

**Validation**: The `group` field must match the directory structure: `{type}/{group}/{item_id}/`

### CLI Usage

#### List Groups

```bash
# Show all groups
python scripts/render_manager.py groups

# With statistics
python scripts/render_manager.py groups -v
```

#### Filter by Group

```bash
# List templates in specific group
python scripts/render_manager.py templates list --group public

# List fragments in group
python scripts/render_manager.py fragments list --group internal -v

# Storage operations by group
python scripts/storage_manager.py list --group research
python scripts/storage_manager.py stats --group public
```

### Python API

```python
from app.templates.registry import TemplateRegistry

registry = TemplateRegistry('/path/to/templates', logger)

# List all groups
groups = registry.list_groups()

# Get items by group
public_templates = registry.list_templates(group='public')

# Get all items with group info
all_templates = registry.list_templates()
for tmpl in all_templates:
    print(f"{tmpl.template_id} ({tmpl.group})")
```

### Group Inheritance

Template fragments inherit the template's group:

```python
# Template 'basic_report' is in 'public' group
schema = registry.get_template_schema('basic_report')

# All embedded fragments inherit 'public' group
for fragment in schema.fragments:
    print(f"{fragment.fragment_id} in group: {fragment.group}")
```

### Error Handling

**Group Mismatch:**
```yaml
# ❌ ERROR: metadata says 'public' but file is in 'research' directory
templates/research/my_template/template.yaml
metadata:
  group: "public"  # Wrong!
```

**Resolution**: Update metadata to match directory:
```yaml
metadata:
  group: "research"  # Correct
```

**Missing Group Field:**
```yaml
# ❌ ERROR: Missing mandatory 'group' field
metadata:
  name: "My Template"
  # group: ???  # Required!
```

### Migration

The system auto-migrates flat structures on first run:

**Before:**
```
templates/
  └── basic_report/
```

**After:**
```
templates/
  └── public/
      └── basic_report/
        (metadata.group set to "public")
```

### Authentication Integration

Groups work with authentication for session isolation:

```
┌─────────────────────┬─────────────────────┐
│  Group: engineering │  Group: research    │
├─────────────────────┼─────────────────────┤
│  sessions: abc-123  │  sessions: xyz-789  │
│  templates: report  │  templates: paper   │
└─────────────────────┴─────────────────────┘

❌ engineering token CANNOT access research sessions
```

See [Authentication Guide](AUTHENTICATION.md) for details.

---

## Proxy Mode

Server-side document storage for large files to avoid network transmission.

### Overview

Proxy mode stores rendered documents on the server and returns only a GUID to the client. Useful for:

- Large PDFs that are expensive to transmit
- Server-side caching and retrieval
- Bandwidth-constrained environments

### How It Works

#### 1. Request with Proxy Mode

```json
{
  "session_id": "abc-123",
  "format": "pdf",
  "proxy": true
}
```

#### 2. Server Stores Document

- Renders document normally
- Stores in `data/proxy/{group}/{guid}.json`
- Returns only the GUID

#### 3. Server Response

```json
{
  "status": "success",
  "data": {
    "proxy_guid": "550e8400-e29b-41d4-a716-446655440000",
    "format": "pdf",
    "content": "",
    "message": "Document stored in proxy mode"
  }
}
```

#### 4. Retrieve Later (Future)

```json
{
  "proxy_guid": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Storage Structure

```
data/proxy/
├── public/
│   └── 550e8400-e29b-41d4-a716-446655440000.json
├── research/
│   └── 660e8400-e29b-41d4-a716-446655440001.json
└── ...
```

Each file contains:

```json
{
  "proxy_guid": "550e8400-e29b-41d4-a716-446655440000",
  "format": "pdf",
  "content": "base64-encoded-content",
  "created_at": "2025-11-23T14:07:10.327Z"
}
```

### API Usage

#### MCP Tool

```python
# Use get_document with proxy=true
response = client.call_tool(
  "get_document",
  {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "format": "pdf",
    "proxy": True
  }
)

# Returns lightweight response
print(response["data"]["proxy_guid"])
```

#### Web API

```bash
# Render with proxy mode
curl -X POST http://localhost:8010/render \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc-123",
    "format": "pdf",
    "proxy": true
  }'
```

### Benefits

- **Reduced Network Overhead** - No base64 encoding/transmission
- **Server-Side Storage** - Documents available for later retrieval
- **Group Segregation** - Documents organized by group
- **Backward Compatible** - Proxy mode is optional

### Configuration

```python
from app.config import Config

# Proxy storage location
proxy_dir = Config.get_proxy_dir()  # "data/proxy"
```

### Future Enhancements

- `get_proxy_document` tool for retrieval
- Auto-expiration with configurable TTL
- Storage limits per group
- Usage monitoring and metrics

---

## Feature Comparison Matrix

| Feature | HTML | PDF | Markdown |
|---------|------|-----|----------|
| **Tables** | Full styling | Full styling | Plain text |
| **Number Formatting** | ✅ | ✅ | ✅ |
| **Table Sorting** | ✅ | ✅ | ✅ |
| **Zebra Stripes** | ✅ | ✅ | ❌ |
| **Border Styles** | ✅ | ✅ | ❌ |
| **Images** | Embedded | Embedded | Linked |
| **Image Sizing** | ✅ | ✅ | ⚠️ (limited) |
| **Proxy Mode** | ✅ | ✅ | ✅ |
| **Groups** | ✅ | ✅ | ✅ |

---

## See Also

- **[Document Generation Guide](DOCUMENT_GENERATION.md)** - Complete workflow
- **[Authentication](AUTHENTICATION.md)** - Security and group isolation
- **[Data Persistence](DATA_PERSISTENCE.md)** - Session and storage
- **[Project Spec](PROJECT_SPEC.md)** - Architecture details
- **[Development Guide](DEVELOPMENT.md)** - Testing and development
