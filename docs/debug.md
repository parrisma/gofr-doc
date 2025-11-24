# Doco Debug Log

## 2025-11-24: Rendering Bug Fix + UUID Handling

### Issue 1: Missing Title/Author in Rendered Documents
**Problem**: Templates expected `{{ title }}` but received nested `global_params={"title": "..."}` dict.

**Fix**: 
1. `app/rendering/engine.py` lines 176-182 - Unpack global_parameters to top level
2. Production templates: `data/docs/templates/public/news_email/document.html.jinja2` - Changed `{{ global_params.email_subject }}` to `{{ email_subject }}`
3. Test templates: `test/render/data/docs/templates/public/news_email/document.html.jinja2` - Changed `{{ global_params.email_subject }}` to `{{ email_subject }}`
4. Mock template: `test/render/test_rendering_engine.py` line 37 - Changed `{{ global_params.get('title', 'Untitled') }}` to `{{ title|default('Untitled') }}`

```python
template_context = {
    **(session.global_parameters or {}),  # Unpack to top level
    "fragments": rendered_fragments,
    "css": css_content,
}
```
**Result**: ✅ All rendering tests pass (550 passed). Title/author now render correctly when global_parameters set.

---

### Issue 2: LLM UUID Modification
**Problem**: OpenWebUI LLM modified session_id `61ea2281-c8df-4719-b71e-56a1305352cc` → `61ea2281-c8df-4719-b77e-56a1305352cc` (changed `b71e` to `b77e`), causing "SESSION_NOT_FOUND" errors.

**Fix**: Enhanced UUID documentation in `app/mcp_server/mcp_server.py`:
- Added CRITICAL warnings to 6 tool session_id parameters (lines 355, 569, 621, 707, 797, 821, 841, 875)
- Enhanced `guid_persistence` section with prominent UUID handling rules
- Added specific `common_pitfalls` entry showing wrong vs right UUID examples

**Key Rules for LLMs**:
- UUIDs are 36 chars: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- Copy/paste ONLY - never retype or modify
- Case-sensitive hex (0-9, a-f) - changing ONE character invalidates UUID
- Example: `b71e ≠ b77e` (different UUIDs)

---

### Issue 3: Restart Script Process Cleanup
**Problem**: MCPO spawns subprocess, pkill didn't kill all processes.

**Fix**: `scripts/restart_servers.sh` - added `kill_and_wait()` function
- Uses multiple kill patterns: "app.main_mcpo", "mcpo --port"
- Polls with pgrep every 0.5s for max 10s until processes die
- Added health checks: MCP (jsonrpc), MCPO (POST /ping), Web (GET /ping)

**Result**: ✅ All processes cleanly terminated and restarted.

---

### Issue 4: Image URL Validation and Embedding
**Problem**: 
1. MCP server used HEAD requests to validate image URLs, but some proxy servers (like OpenWebUI) return HTTP 405 Method Not Allowed
2. Images were stored as URLs but not embedded in HTML/PDF, causing rendering issues
3. No tests verified images actually appeared in rendered documents

**Fixes**:
1. **Image Validation** (`app/validation/image_validator.py` line 93)
   - Changed from `client.head(url)` to `client.get(url)`
   - Downloads image during validation to enable embedding

2. **Image Embedding** (`app/mcp_server/mcp_server.py` lines 1315-1330)
   - Downloads image when adding fragment via `add_image_fragment`
   - Converts to base64 data URI for embedding
   - Stores both original URL and embedded data URI
   - Template uses `embedded_data_uri` for HTML/PDF, falls back to URL

3. **Test Coverage** (`test/mcp/test_image_rendering.py`)
   - Added 3 integration tests verifying images appear in rendered output
   - Tests HTML rendering with embedded images
   - Tests PDF generation includes images
   - Tests multiple images in same document

**Result**: 
✅ Image validation works with proxy endpoints that don't support HEAD
✅ Images are downloaded and embedded in HTML/PDF output
✅ Markdown output includes data URIs (acceptable for testing/drafting)
✅ Full test coverage prevents regression
✅ PDF format validation using pypdf library verifies:
   - Valid PDF structure and page count
   - Document metadata (title, producer)
   - Text content extraction
   - Embedded image detection (XObjects with /Image subtype)
   - Image dimensions verification

---

### Issue 5: Image Embedding for HTML/PDF Output
**Problem**: Images were referenced by URL in all output formats. For HTML/PDF, images should be embedded (downloaded and base64-encoded as data URIs) to enable offline viewing and proper PDF generation. For Markdown, URLs are correct.

**Fix**: 
1. `app/mcp_server/mcp_server.py` lines 1126-1148 - Download image when adding fragment
   - Uses httpx to GET image content
   - Creates base64-encoded data URI (e.g., `data:image/png;base64,...`)
   - Stores both `image_url` (for Markdown) and `embedded_data_uri` (for HTML/PDF)
   - Graceful fallback if download fails

2. `test/render/data/docs/templates/public/basic_report/fragments/image_from_url.html.jinja2`
   - Changed from `<img src="{{ image_url }}">` to `<img src="{{ embedded_data_uri|default(image_url) }}">`
   - Uses embedded data URI when available, falls back to URL

3. `test/render/data/docs/templates/public/basic_report/template.yaml`
   - Added `embedded_data_uri` parameter to image_from_url fragment schema
   - Marked as optional and automatically injected

4. Enhanced tests in `test/mcp/test_image_rendering.py`
   - Verify HTML contains `data:image/` embedded URIs
   - Verify PDF contains `/Image` or `/XObject` references
   - Verify PDF size increases with embedded image data

**Key Behavior**:
- **HTML/PDF**: Images embedded as base64 data URIs → works offline, proper PDF generation
- **Markdown**: Images remain as URL links → standard Markdown behavior
- **Fallback**: If download fails, URL is used in all formats

**Result**: ✅ All 560 tests passing. Images properly embedded in HTML/PDF, linked in Markdown.

---

## Verification Commands

```bash
# Check session status
curl -s -X POST http://localhost:8011/get_session_status \
  -H "Content-Type: application/json" \
  -d '{"session_id": "YOUR-UUID-HERE"}'

# Render document
curl -s -X POST http://localhost:8011/get_document \
  -H "Content-Type: application/json" \
  -d '{"session_id": "YOUR-UUID-HERE", "format": "md"}' \
  | python -c "import json, sys; d=json.load(sys.stdin); print(d['data']['content'])"

# Restart all servers
./scripts/restart_servers.sh
```

---

## Standard Ports
- MCP: 8010
- MCPO: 8011 
- WEB: 8012

---

## Known LLM Issues
1. **Hallucination**: LLM claims to call tools without actually calling them
2. **UUID Mutation**: LLM modifies UUID characters during tool call chains
3. **Workaround**: Enhanced documentation with explicit CRITICAL warnings about UUID preservation
