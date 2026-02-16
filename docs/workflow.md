# Workflow Guide

This guide explains the typical steps to use the `gofr-doc` document generation tools.

For a complete list of parameters, see the **[Tool Reference](tools.md)**.

## Typical Process

1.  **Discover**: Find templates, fragments, and styles.
2.  **Session**: Create a document session with an alias.
3.  **Configure**: Set global parameters (title, author, etc.).
4.  **Build**: Add content fragments (headings, paragraphs, tables, images).
5.  **Render**: Generate the finished document (HTML, PDF, or Markdown).

---

## 1. Discover Templates and Styles

Before creating a document, explore what's available.

**List templates:**
```json
// list_templates — no parameters
```

**Inspect a template's schema:**
```json
{"template_id": "basic_report"}
```

**List fragments in a template:**
```json
{"template_id": "basic_report"}
```

**Get a fragment's parameter schema:**
```json
{"template_id": "basic_report", "fragment_id": "table"}
```

**List available styles:**
```json
// list_styles — no parameters
```

These tools require no authentication.

---

## 2. Create a Session

Every document starts with a session. Sessions are backed by a template and
identified by a friendly alias.

```json
{"template_id": "basic_report", "alias": "q4-report"}
```

**Alias rules:**
- 3–64 characters: letters, numbers, hyphens, underscores.
- Unique within your group. Reusable across groups.
- Good: `q4-report`, `invoice-march-2024`, `weekly_summary`
- Bad: `x`, `my report`, `report!!!!`

**Important:** All subsequent tools accept either the alias or the UUID in
the `session_id` field — use the alias for readability.

---

## 3. Set Global Parameters

Global parameters apply to the entire document (title, author, date, etc.).
They **must** be set before rendering.

```json
{
  "session_id": "q4-report",
  "parameters": {
    "title": "Q4 Report",
    "author": "Data Team"
  }
}
```

Can be called multiple times — values are merged.

**Tip:** Use `validate_parameters` first to catch mistakes without modifying
the session:
```json
{
  "template_id": "basic_report",
  "parameter_type": "global",
  "parameters": {"title": "Q4 Report", "author": "Data Team"}
}
```

---

## 4. Build Content with Fragments

Add fragments in sequence to assemble the document body.

### Headings and Paragraphs

```json
{"session_id": "q4-report", "fragment_id": "heading", "parameters": {"text": "Executive Summary"}}
```
```json
{"session_id": "q4-report", "fragment_id": "paragraph", "parameters": {"text": "This quarter saw record growth..."}}
```

### Tables

Tables support formatting, sorting, and column alignment:

```json
{
  "session_id": "q4-report",
  "fragment_id": "table",
  "parameters": {
    "rows": [
      ["Product", "Sales", "Profit Margin"],
      ["Widget A", "125000", "0.35"],
      ["Widget B", "98000", "0.42"]
    ],
    "has_header": true,
    "title": "Product Performance",
    "column_alignments": ["left", "right", "center"],
    "number_format": {"1": "currency:USD", "2": "percent"},
    "sort_by": {"column": "Sales", "order": "desc"}
  }
}
```

### Images

Images are validated immediately (HTTP HEAD request at add time):

```json
{
  "session_id": "q4-report",
  "image_url": "https://cdn.example.com/chart.png",
  "width": 800,
  "alt_text": "Q4 Sales Chart",
  "alignment": "center"
}
```

Set only width **or** height — setting both causes distortion.

### Fragment Positioning

By default fragments are appended to the end. You can control placement:

| Position | Behaviour |
|----------|-----------|
| `"end"` | Append to bottom (default). |
| `"start"` | Prepend to top. |
| `"before:<guid>"` | Insert before the fragment with matching GUID. |
| `"after:<guid>"` | Insert after the fragment with matching GUID. |

Save the `fragment_instance_guid` returned by `add_fragment` — you need it
for positional inserts and `remove_fragment`.

---

## 5. Render the Document

Once globals are set and fragments are added, render the output:

```json
{"session_id": "q4-report", "format": "html"}
```

Formats: `html`, `pdf` (base64-encoded), `md` (Markdown).

You can apply a style:
```json
{"session_id": "q4-report", "format": "html", "style_id": "bizdark"}
```

Sessions are reusable — re-render with different formats or styles as many
times as needed.

### Proxy Mode (Large Documents)

For large documents, use proxy mode to store the rendered output server-side
and get a download URL instead of inline content:

```json
{"session_id": "q4-report", "format": "pdf", "proxy": true}
```

Returns `proxy_guid` and `download_url`. Retrieve via:

```
GET http://server:8042/proxy/{proxy_guid}
Authorization: Bearer <token>
```

**Key distinction:** `session_id` is the recipe (reusable), `proxy_guid` is
the baked output (one specific render). One session can produce many proxy documents.

Proxy documents persist even after the session is aborted.

---

## 6. Clean Up

Delete a session when you're done:

```json
{"session_id": "q4-report"}
```

This is irreversible — all session data is permanently deleted.

---

## GUID Lifecycle

Three types of GUIDs exist in the system:

| GUID | Created By | Purpose |
|------|------------|---------|
| `session_id` | `create_document_session` | Document config. Reusable. Lives until `abort_document_session`. |
| `fragment_instance_guid` | `add_fragment` / `add_image_fragment` | Identifies a specific fragment instance. Used for `remove_fragment` and positional inserts. |
| `proxy_guid` | `get_document(proxy=true)` | One rendered output. **Not** the session_id. Persists after session deletion. |

Always copy/paste GUIDs exactly — never retype or truncate them.

---

## Common Pitfalls

**Session management:**
- Not saving `session_id` immediately after creation.
- Retyping UUIDs instead of copy/pasting (`b71e ≠ b77e`).
- Forgetting to set global parameters before rendering.

**Proxy confusion:**
- Confusing `session_id` with `proxy_guid` — they are different GUIDs.
- Downloading via `/proxy/{session_id}` instead of `/proxy/{proxy_guid}`.
- Missing `Authorization` header on proxy downloads.

**Tables:**
- Column widths totalling > 100%.
- Using 1-based column indices (must be 0-based).
- Wrong number format syntax — use `currency:USD`, not `USD`.
- Using `sort_by` column name when there's no header row.

**Images:**
- Image behind a login wall or firewall (URL must be publicly accessible).
- HTTP URL without setting `require_https=false`.
- Setting both `width` and `height` (causes distortion — set only one).
- Images exceeding the 10 MB limit.
