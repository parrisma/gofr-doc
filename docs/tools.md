# Tool Reference

Complete reference for every MCP tool exposed by **gofr-doc**.
Auto-generated from the live code — treat this as the authoritative source.

---

## Discovery Tools

Tools for exploring templates, fragments, and styles. No authentication required.

---

### ping

Health check. Returns `{status: "ok", service: "gofr-doc"}` when the server is reachable.
Call this first to verify connectivity.

**Parameters:** none

---

### help

Returns comprehensive workflow guidance, GUID lifecycle rules, common pitfalls,
example workflows, and tool sequencing guide.

**Parameters:** none

---

### list_templates

List all available document templates with their IDs, names, descriptions, and groups.

**Parameters:** none

---

### get_template_details

Get the full schema for a specific template including required global parameters
and embedded fragment definitions.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| template_id | string | yes | — | Template identifier from `list_templates`. |
| token | string | no | — | JWT token for authentication. |

**Returns:** `{template_id, name, description, global_parameters[], fragments[]}`

**Errors:** TEMPLATE_NOT_FOUND

---

### list_template_fragments

List all fragments available within a specific template.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| template_id | string | yes | — | Template identifier. |
| token | string | no | — | JWT token for authentication. |

**Returns:** `{template_id, fragments: [{fragment_id, name, description, parameter_count}, ...]}`

**Errors:** TEMPLATE_NOT_FOUND

---

### get_fragment_details

Get the parameter schema for a specific fragment — required/optional parameters,
types, defaults, examples, and validation rules.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| template_id | string | yes | — | Template identifier. |
| fragment_id | string | yes | — | Fragment identifier from `list_template_fragments`. |
| token | string | no | — | JWT token for authentication. |

**Returns:** `{template_id, fragment_id, name, description, parameters[]}`

**Errors:** FRAGMENT_NOT_FOUND, TEMPLATE_NOT_FOUND

---

### list_styles

List all available visual styles for document rendering.

**Parameters:** none

---

## Stock Images (Web Server)

The web server hosts stock images for use in documents. Images are served
publicly (no authentication required) and can be referenced by URL in
`add_image_fragment`. Subdirectory structure is preserved.

---

### GET /images

List all available stock images.

**Parameters:** none

**Returns:** `{"status": "success", "data": {"images": ["piggy-bank.jpg", "logos/acme.png"], "count": 2}}`

Images are returned as relative paths, recursively discovered. Only image files
are listed (png, jpg, jpeg, svg, webp, gif, avif, tiff, bmp, ico).

---

### GET /images/{path}

Serve a stock image file by relative path.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string (URL path) | yes | Relative path within the images directory. Supports subdirectories. |

**Returns:** Image binary with correct `Content-Type` and `Cache-Control: public, max-age=3600`.

**Errors:** 404 if not found, 400 if path traversal detected, 415 if not an image file.

**Example:** `GET /images/piggy-bank.jpg` or `GET /images/logos/acme.png`

---

## Session Management

Tools for creating, inspecting, and deleting document sessions.
Authentication required unless noted.

---

### create_document_session

Create a new document session based on a template. Returns a session UUID and alias.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| template_id | string | yes | — | Template identifier defining the document structure. |
| alias | string | yes | — | Friendly name (3–64 chars: letters, numbers, hyphens, underscores). E.g. `q4-report-2025`. |
| token | string | no | — | JWT token for authentication. |

**Returns:** `{session_id, alias, template_id, created_at, updated_at}`

**Errors:** TEMPLATE_NOT_FOUND, AUTH_REQUIRED, AUTH_FAILED

---

### get_session_status

Get the current state of a session — readiness for rendering, global parameter
status, and fragment count.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| session_id | string | yes | — | Session alias or UUID. |
| token | string | no | — | JWT token for authentication. |

**Returns:** `{session_id, template_id, has_global_parameters, fragment_count, is_ready_to_render, created_at, updated_at}`

**Errors:** SESSION_NOT_FOUND, AUTH_REQUIRED, AUTH_FAILED

---

### list_active_sessions

List all document sessions in the caller's group with summary info including aliases.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| token | string | no | — | JWT token (injected via auth). |

**Returns:** `{sessions: [{session_id, alias, template_id, fragment_count, has_global_parameters, group, created_at, updated_at}, ...], session_count}`

**Errors:** AUTH_REQUIRED, AUTH_FAILED

---

### abort_document_session

Permanently delete a session and all its data. **Irreversible.**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| session_id | string | yes | — | Session alias or UUID. |
| token | string | no | — | JWT token for authentication. |

**Returns:** Deletion confirmation.

**Errors:** SESSION_NOT_FOUND, AUTH_REQUIRED, AUTH_FAILED

---

## Validation

---

### validate_parameters

Pre-flight validation — check if parameters are valid before saving.
Catches mistakes early without modifying session state.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| template_id | string | yes | — | Template identifier to validate against. |
| parameters | object | yes | — | Parameter values to validate. |
| parameter_type | string | yes | `"global"` | `"global"` or `"fragment"`. |
| fragment_id | string | no | — | Required when `parameter_type="fragment"`. |
| token | string | no | — | JWT token for authentication. |

**Returns:** `{is_valid, errors: [{parameter, expected_type, received_type, message, examples}, ...]}`

**Errors:** TEMPLATE_NOT_FOUND, VALIDATION_ERROR, AUTH_REQUIRED, AUTH_FAILED

---

## Content Building

Tools for populating a session with global parameters and content fragments.
Authentication required.

---

### set_global_parameters

Set or update global parameters (title, author, date, etc.) that apply to the
entire document. Can be called multiple times — values are merged.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| session_id | string | yes | — | Session alias or UUID. |
| parameters | object | yes | — | Dict of global parameter values. Keys match template schema. E.g. `{title: "Q4 Report", author: "John"}`. |
| token | string | no | — | JWT token for authentication. |

**Returns:** Updated session state with current `global_parameters`.

**Errors:** SESSION_NOT_FOUND, INVALID_GLOBAL_PARAMETERS, AUTH_REQUIRED, AUTH_FAILED

---

### add_fragment

Add a content fragment (heading, paragraph, table, etc.) to the document body.
Call repeatedly to build the document content.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| session_id | string | yes | — | Session alias or UUID. |
| fragment_id | string | yes | — | Fragment type from `list_template_fragments` (e.g. `heading`, `paragraph`, `table`). |
| parameters | object | yes | — | Fragment-specific parameters (use `get_fragment_details` to discover). |
| position | string | no | `"end"` | Insert position: `end`, `start`, `before:<guid>`, `after:<guid>`. |
| token | string | no | — | JWT token for authentication. |

**Returns:** `{fragment_instance_guid, position, fragment_id, ...}`

Save the returned `fragment_instance_guid` — you need it for `remove_fragment` or positional inserts.

**Errors:** SESSION_NOT_FOUND, FRAGMENT_NOT_FOUND, INVALID_FRAGMENT_PARAMETERS, INVALID_POSITION, INVALID_SESSION_STATE, AUTH_REQUIRED, AUTH_FAILED

---

### add_image_fragment

Add an image from a URL with **immediate URL validation** (HTTP HEAD request at
add time, not render time). Downloads and embeds as base64 for HTML/PDF output.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| session_id | string | yes | — | Session alias or UUID. |
| image_url | string | yes | — | Publicly accessible image URL. Validated immediately. Allowed types: `image/png`, `image/jpeg`, `image/gif`, `image/webp`, `image/svg+xml`. |
| title | string | no | — | Caption displayed above the image. |
| width | integer | no | — | Target width in pixels (height scales proportionally). |
| height | integer | no | — | Target height in pixels (width scales proportionally). |
| alt_text | string | no | title or `"Image"` | Accessibility text for screen readers. |
| alignment | string | no | `"center"` | Horizontal alignment: `left`, `center`, `right`. |
| require_https | boolean | no | `true` | Enforce HTTPS. Set `false` only for localhost/dev. |
| position | string | no | `"end"` | Insert position: `end`, `start`, `before:<guid>`, `after:<guid>`. |
| token | string | no | — | JWT token for authentication. |

**Returns:** `{fragment_instance_guid, ...}` or detailed validation error.

**Errors:** SESSION_NOT_FOUND, INVALID_IMAGE_URL, IMAGE_URL_NOT_ACCESSIBLE, INVALID_IMAGE_CONTENT_TYPE, IMAGE_TOO_LARGE, IMAGE_URL_TIMEOUT, IMAGE_VALIDATION_ERROR, AUTH_REQUIRED, AUTH_FAILED

---

### remove_fragment

Remove a specific fragment instance from the document by its GUID.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| session_id | string | yes | — | Session alias or UUID. |
| fragment_instance_guid | string | yes | — | Unique fragment instance GUID (from `add_fragment` response or `list_session_fragments`). |
| token | string | no | — | JWT token for authentication. |

**Returns:** Confirmation with updated fragment count.

**Errors:** SESSION_NOT_FOUND, FRAGMENT_NOT_FOUND, AUTH_REQUIRED, AUTH_FAILED

---

### list_session_fragments

List all fragments currently in the document in display order, with GUIDs, types,
parameters, and positions.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| session_id | string | yes | — | Session alias or UUID. |
| token | string | no | — | JWT token for authentication. |

**Returns:** `{fragments: [{guid, fragment_id, parameters, created_at, position}, ...]}`

**Errors:** SESSION_NOT_FOUND, AUTH_REQUIRED, AUTH_FAILED

---

## Rendering

---

### get_document

Render the finished document in HTML, PDF, or Markdown.
Supports proxy mode for large documents.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| session_id | string | yes | — | Session alias or UUID. |
| format | string | yes | — | Output format: `html`, `pdf`, `md`. PDF is base64-encoded. |
| style_id | string | no | default style | Style identifier from `list_styles`. |
| proxy | boolean | no | `false` | If `true`, stores document server-side and returns `proxy_guid` + `download_url` instead of inline content. |
| token | string | no | — | JWT token for authentication. |

**Returns:** `{content, format, session_id, rendered_at, proxy_guid?, download_url?}`

Content is `null` when `proxy=true`.

**Errors:** SESSION_NOT_FOUND, SESSION_NOT_READY, RENDER_FAILED, STYLE_NOT_FOUND, AUTH_REQUIRED, AUTH_FAILED

---

## Plot Tools

Tools for rendering graphs, managing plot images, and embedding charts in documents.
Migrated from gofr-plot into gofr-doc.

---

### list_themes

Discover all available visual themes with descriptions.
No authentication required.

**Parameters:** none

**Returns:** `{themes: {name: description, ...}, count}`

Available themes: light, dark, bizlight, bizdark.

---

### list_handlers

Discover all available chart types (handlers) with capability descriptions.
No authentication required.

**Parameters:** none

**Returns:** `{handlers: {name: description, ...}, count}`

Available types: line, scatter, bar.

---

### render_graph

Render a graph visualization and return it as a base64-encoded image or storage GUID.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| title | string | yes | -- | Graph title. |
| y1 | number[] | yes* | -- | First dataset Y-axis data. (*or legacy `y`) |
| x | number[] | no | indices | X-axis data points. |
| y2-y5 | number[] | no | -- | Additional datasets (up to 5 total). |
| label1-label5 | string | no | -- | Legend labels per dataset. |
| color1-color5 | string | no | theme default | Colors per dataset. |
| xlabel | string | no | X-axis | X-axis label. |
| ylabel | string | no | Y-axis | Y-axis label. |
| type | string | no | line | Chart type: line, scatter, bar. |
| format | string | no | png | Output: png, jpg, svg, pdf. |
| theme | string | no | light | Visual theme: light, dark, bizlight, bizdark. |
| proxy | boolean | no | false | If true, save to storage and return GUID. |
| alias | string | no | -- | Friendly name for proxy mode. |
| line_width | number | no | 2.0 | Line width. |
| marker_size | number | no | 36.0 | Scatter marker size. |
| alpha | number | no | 1.0 | Transparency (0.0-1.0). |
| xmin/xmax | number | no | -- | X-axis limits. |
| ymin/ymax | number | no | -- | Y-axis limits. |
| x_major_ticks | number[] | no | -- | Custom X major tick positions. |
| y_major_ticks | number[] | no | -- | Custom Y major tick positions. |
| auth_token | string | yes | -- | JWT authentication token. |

**Returns (non-proxy):** ImageContent (base64 image) + metadata.

**Returns (proxy):** `{guid, format, theme, type, title, size_bytes, alias?}`

**Errors:** INVALID_GRAPH_PARAMS, GRAPH_VALIDATION_ERROR, RENDER_ERROR, PLOT_NOT_INITIALIZED

---

### get_image

Retrieve a previously stored graph image by GUID or alias.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| identifier | string | yes | -- | Image GUID or alias. |
| auth_token | string | yes | -- | JWT authentication token. |

**Returns:** ImageContent (base64 image) + metadata `{identifier, format, size_bytes, alias}`.

**Errors:** IMAGE_NOT_FOUND, PLOT_STORAGE_NOT_INITIALIZED

---

### list_images

List all stored plot images accessible to your token's group.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| auth_token | string | yes | -- | JWT authentication token. |

**Returns:** `{images: [{guid, format, alias, size, created_at}, ...], count}`

**Errors:** PLOT_STORAGE_NOT_INITIALIZED

---

### add_plot_fragment

Render a graph and embed it as a fragment in a document session.
Supports two modes: GUID path (embed previously rendered plot) or inline path (render and embed).

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| session_id | string | yes | -- | Document session GUID or alias. |
| plot_guid | string | no | -- | GUID of previously rendered plot (GUID path). |
| title | string | yes* | -- | Graph title (*required for inline path). |
| y1 | number[] | yes* | -- | First dataset (*required for inline path). |
| x, y2-y5, label1-label5, color1-color5 | various | no | -- | Render params (inline path). |
| type, format, theme | string | no | line/png/light | Chart settings (inline path). |
| width | integer | no | -- | Image width in pixels. |
| height | integer | no | -- | Image height in pixels. |
| alt_text | string | no | -- | Accessibility text. |
| alignment | string | no | center | left, center, right. |
| position | string | no | end | Fragment position: end, start, before:<guid>, after:<guid>. |
| auth_token | string | yes | -- | JWT authentication token. |

**Returns:** Fragment output with fragment_instance_guid.

**Errors:** SESSION_NOT_FOUND, IMAGE_NOT_FOUND, INVALID_GRAPH_PARAMS, GRAPH_VALIDATION_ERROR, RENDER_ERROR

---

## Error Codes

Every error response includes `{success: false, error_code, error, recovery_strategy}`.
The `recovery_strategy` field provides actionable guidance.

### Authentication Errors

| Error Code | Recovery Strategy |
|------------|-------------------|
| AUTH_REQUIRED | Provide a valid JWT token in `auth_token`. |
| AUTH_FAILED | Token verification failed (expired, invalid, malformed). Obtain a fresh token. |

### Input & Validation Errors

| Error Code | Recovery Strategy |
|------------|-------------------|
| INVALID_ARGUMENTS | Check `inputSchema` for required parameters and types. |
| UNKNOWN_TOOL | Use one of the tools listed in this reference. |
| INVALID_OPERATION | Business rule violation. Review error message. |
| VALIDATION_ERROR | Adjust request parameters per error details. |
| PYDANTIC_VALIDATION_ERROR | Schema validation failure. Check error details. |

### Resource Errors

| Error Code | Recovery Strategy |
|------------|-------------------|
| SESSION_NOT_FOUND | Verify `session_id`. Call `list_active_sessions` to discover sessions. |
| TEMPLATE_NOT_FOUND | Use `list_templates` for available templates. |
| FRAGMENT_NOT_FOUND | Call `list_session_fragments` for current GUIDs. |
| STYLE_NOT_FOUND | Use `list_styles` for available styles. |
| RESOURCE_NOT_FOUND | Verify resource ID. |

### Session & Rendering Errors

| Error Code | Recovery Strategy |
|------------|-------------------|
| INVALID_GLOBAL_PARAMETERS | Call `get_template_details` for required globals. |
| INVALID_FRAGMENT_PARAMETERS | Call `get_fragment_details` for required params. |
| INVALID_POSITION | Use `start`, `end`, `before:<guid>`, `after:<guid>`. |
| INVALID_SESSION_STATE | Ensure globals are set before adding fragments or rendering. |
| SESSION_NOT_READY | Set global params, add fragments, then render. |
| RENDER_FAILED | Check `style_id`, `format`, and session content. |

### Table-Specific Errors

| Error Code | Recovery Strategy |
|------------|-------------------|
| INVALID_TABLE_DATA | Ensure consistent row lengths and valid column indices. |
| INVALID_COLOR | Use theme names or hex `#RRGGBB` / `#RGB`. |
| NUMBER_FORMAT_ERROR | Use `currency:USD`, `percent`, `decimal:2`, `integer`, `accounting`. |
| INVALID_COLUMN_WIDTH | Percentages must total ≤ 100%. |

### Image-Specific Errors

| Error Code | Recovery Strategy |
|------------|-------------------|
| INVALID_IMAGE_URL | Non-HTTPS URL with `require_https=true`. Allow HTTP only for dev. |
| IMAGE_URL_NOT_ACCESSIBLE | URL returned 404/403/500 on HEAD request. Verify URL is accessible. |
| INVALID_IMAGE_CONTENT_TYPE | URL returns non-image content-type. Ensure URL points to an image. |
| IMAGE_TOO_LARGE | File exceeds 10 MB limit. Use a smaller image. |
| IMAGE_URL_TIMEOUT | Server unreachable or slow. Check URL and retry. |
| IMAGE_VALIDATION_ERROR | Generic image validation failure. Check image URL and format. |

### Plot-Specific Errors

| Error Code | Recovery Strategy |
|------------|-------------------|
| PLOT_NOT_INITIALIZED | Plot subsystem failed to initialize. Restart the server. |
| PLOT_STORAGE_NOT_INITIALIZED | Plot storage requires CommonStorageAdapter. Check server config. |
| INVALID_GRAPH_PARAMS | Invalid graph parameters. Check title is provided and at least y1 array exists. |
| GRAPH_VALIDATION_ERROR | Data validation failed. Review validation_errors in details. Fix arrays and retry. |
| RENDER_ERROR | Rendering failed. Check data arrays are non-empty and of equal length. |
| IMAGE_NOT_FOUND | Plot image GUID or alias not found. Call list_images to see available images. |
| MISSING_TITLE | Title required for inline render mode. Provide title or use plot_guid instead. |

### Server Errors

| Error Code | Recovery Strategy |
|------------|-------------------|
| UNEXPECTED_ERROR | Unhandled exception. Check server logs. |
| INTERNAL_ERROR | Generic server error. Report if it persists. |
| CONFIGURATION_ERROR | Check server configuration. Contact administrator. |
| REGISTRY_ERROR | Verify template/fragment/style ID exists. |
| SECURITY_ERROR | Check token has access to the requested resource. |
