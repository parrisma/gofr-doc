# gofr-plot → gofr-doc (Tools + Functional Tests) Migration Plan

## Scope (explicit)

**In scope**
- Migrate **gofr-plot functional capability** into gofr-doc:
  - MCP tools (graph rendering + image retrieval + discovery)
  - Functional tests that validate those tools end-to-end
- Keep gofr-doc’s **operational machinery** unchanged:
  - Docker / compose / entrypoint / ports / housekeeper patterns remain as-is
  - Existing gofr-doc MCP/MCPO/Web services remain the runtime model

**Out of scope**
- Bringing over gofr-plot’s separate web service (`/render`, `/proxy/{guid}/html`, etc.) as a new service.
- Duplicating gofr-plot’s security framework (rate limiter / sanitizer / auditor) unless a specific gap is identified.

## What gofr-plot provides (functional inventory)

### MCP tools
From gofr-plot `app/mcp_server/mcp_server.py`, the functional tool surface area is:
- `ping` (no auth)
- `render_graph` (auth required, supports proxy mode)
- `get_image` (auth required)
- `list_images` (auth required)
- `list_themes` (no auth)
- `list_handlers` (no auth)

### Chart capabilities
- Chart types/handlers: `line`, `scatter`, `bar`
- Themes: `light`, `dark`, `bizlight`, `bizdark`
- Output formats: `png`, `jpg`, `svg`, `pdf`
- Multi-dataset: `y1..y5` with optional labels/colors
- Axis controls: `xmin/xmax/ymin/ymax`, major/minor ticks
- Proxy mode:
  - `render_graph(proxy=true)` persists output and returns a GUID
  - `get_image(identifier=guid|alias)` retrieves a persisted image
  - Alias support for proxy artifacts

### Dependencies
gofr-plot adds only a few project-specific deps on top of gofr-common:
- `matplotlib`
- `numpy` (used by grouped bar chart handler)

## Compatibility mapping: gofr-plot vs gofr-doc

### Auth / group model
- gofr-doc: JWT auth injects `group` from token; tools can be token-optional (discovery set).
- gofr-plot: tools take `token` argument and derive a single `group`.

**Migration target**
- Adopt the gofr-dig MCP pattern so gofr-doc + plot tools are one seamless toolset:
  - Tools that require group scoping accept a tool parameter named `auth_token`.
  - `auth_token` may be the raw JWT or prefixed with `Bearer ` (gofr-dig tolerates both).
  - If both a tool parameter token and an HTTP `Authorization: Bearer ...` header are present, the **tool parameter takes precedence** (matches gofr-doc’s existing precedence behavior).
  - If a token grants access to multiple groups, the **first group** is treated as the primary group for write-scoped activity (matches gofr-dig: `token_info.groups[0]`).
  - gofr-doc’s `handle_call_tool()` group-injection model remains the enforcement mechanism; plot handlers must treat injected `group` as authoritative.

### Storage model
- gofr-doc: `DocumentStorageBase` with `save_document/get_document` etc.
- gofr-plot: `ImageStorageBase` with `save_image/get_image`, alias resolution.

**Migration target**
- Prefer reusing the **same gofr-common storage implementation** gofr-doc already wraps (`gofr_common.storage.FileStorage`).
- Keep the storage mechanism unified (same library/code path), but segregate document vs plot artifacts **without** introducing a second storage service.

Recommended approach (simple + compatible with gofr-common):
- Use a single underlying blob store (same `FileStorage` / metadata.json / blob repository).
- Segregate plot artifacts from document artifacts via **metadata and naming**, not separate services:
  - Store plot renders with metadata like `artifact_type="plot_image"` (extra fields in gofr-common metadata).
  - Optionally store a `plot_alias` field (user-friendly) in metadata extra fields for alias resolution.
  - Keep group ownership enforcement via gofr-common metadata `group` and access checks.

Why metadata segregation (vs multiple storage instances)?
- gofr-common `FileStorage.save()` already accepts `**kwargs` stored in metadata extra fields.
- gofr-common `FileStorage.get()` returns `(bytes, format)` so we get image bytes + format without inventing a new storage mechanism.
- A thin “plot storage wrapper” can implement:
  - `list_images(group)` by filtering metadata entries to `artifact_type == "plot_image"`
  - `resolve_identifier(identifier, group)` using `plot_alias` (to avoid alias collisions with other artifact types)
  - `get_image(guid, group)` delegating to `FileStorage.get(guid, group)`

### Web proxy endpoints
- gofr-doc already has `GET /proxy/{proxy_guid}` for document proxy artifacts.
- gofr-plot has `GET /proxy/{identifier}` for image proxy artifacts.

**Migration target**
- Do **not** add a second meaning to `/proxy/{...}` in the existing gofr-doc web server.
- Keep image retrieval through MCP tool `get_image` as the functional surface.
- If HTTP retrieval is later required, add a new path namespace (e.g. `/plot-proxy/{guid}`) to avoid collisions.

### Embedding plot images in documents

gofr-doc already provides an `add_image_fragment` tool and an `image_from_url` fragment type.
At add-time the tool downloads the image, validates it, and embeds it as a base64 data URI
(`data:image/png;base64,...`). At render-time the fragment template uses the embedded data:

```jinja
<img src="{{ embedded_data_uri|default(image_url) }}" ... />
```

This means rendered HTML and PDF documents are self-contained — no external HTTP endpoint is required to display the plot.

**Migration target — `add_plot_fragment` convenience tool**

Add a single new MCP tool that bridges the plot and document systems:

| Field | Value |
|---|---|
| Tool name | `add_plot_fragment` |
| Auth | `auth_token` (gofr-dig convention) |
| Required params | `session_id` (document session GUID or alias), plus **one of**: `plot_guid` (GUID of a previously rendered plot) **or** inline render params (`x`, `y1`, `handler`, etc.) |
| Optional params | `title`, `width`, `height`, `alt_text`, `alignment`, `position` (same as `add_image_fragment`) |
| Behaviour | See sequence below |

**Sequence (GUID path — preferred for pre-rendered plots)**
1. Caller renders a graph: `render_graph(proxy=true, ...)` → receives `plot_guid`.
2. Caller calls `add_plot_fragment(session_id, plot_guid=<guid>)`.
3. Tool internally:
   a. Fetches the stored image bytes from FileStorage via `plot_guid` (same group enforcement).
   b. Builds a `data:image/png;base64,...` URI from the bytes.
   c. Adds an `image_from_url` fragment to the document session with `embedded_data_uri` pre-populated.
4. No HTTP round-trip, no new endpoint. The document renders the plot inline.

**Sequence (inline render path — render-and-embed in one call)**
1. Caller calls `add_plot_fragment(session_id, x=[...], y1=[...], handler="bar", ...)`.
2. Tool internally:
   a. Renders the graph in-process (same code path as `render_graph`, proxy=false).
   b. Takes the resulting PNG bytes and builds the data URI directly.
   c. Adds the `image_from_url` fragment to the session.
3. No storage round-trip for the plot — it is rendered and embedded in one step.

**Why this is better than URL-based injection**
- **Self-contained**: HTML/PDF output contains the image inline; no server must be running to view it.
- **No new HTTP endpoint**: everything flows through MCP tools + FileStorage.
- **Offline-safe**: exported PDFs work without network access.
- **Reuses existing fragment infra**: the `image_from_url` fragment template, Jinja2 rendering, and position insertion all work unchanged.

**URL-based injection still works**
The existing `add_image_fragment` tool already accepts any externally-hosted `image_url`.
If a user wants to reference a plot hosted elsewhere (CDN, another service), they use `add_image_fragment` with the URL — no changes needed.

**Future HTTP retrieval**
If an HTTP endpoint is later needed (e.g., for embedding in external Markdown that cannot handle data URIs):
- Add `/plot-proxy/{guid}` as a **new** path namespace in the gofr-doc web server.
- Never overload the existing `/proxy/{proxy_guid}` document proxy.

## Step-by-step migration plan

### Step 0 — Create a working branch
1. Create branch `feature/plot-tools`.
2. Keep commits small: one for deps, one for core tool plumbing, one for tests.

### Step 1 — Add plotting dependencies to gofr-doc
1. Add to gofr-doc `pyproject.toml` dependencies:
   - `matplotlib>=3.5.0`
   - `numpy` (version pin not required unless CI breaks)
2. Verify `pip install -e .` works in dev container.

Acceptance
- `python -c "import matplotlib, numpy"` succeeds inside gofr-doc env.

### Step 2 — Add plot domain modules under gofr-doc `app/plot/`
Create a minimal “plot domain” package (names are suggestions; keep consistent with gofr-doc conventions):
- `app/plot/graph_params.py` (ported from gofr-plot `GraphParams`)
- `app/plot/handlers/` (`line/scatter/bar`, registry)
- `app/plot/themes/` (`light/dark/bizlight/bizdark`, registry)
- `app/plot/validation/` (port GraphDataValidator; optionally omit sanitizer initially)
- `app/plot/render/renderer.py` (GraphRenderer)

Notes
- Keep imports **internal to gofr-doc**, not referencing gofr-plot package paths.
- Use gofr-doc logging style (its `Logger` wrapper) rather than gofr-plot’s `ConsoleLogger`.

Acceptance
- Unit tests for handlers/themes/validation can run without starting servers.

### Step 3 — Implement plot storage adapter in gofr-doc
Add a thin plot-storage wrapper around the existing gofr-doc/gofr-common storage:
- Reuse the same gofr-common `FileStorage` implementation already used by gofr-doc.
- Keep docs + plots in one storage mechanism, but tag plot artifacts in metadata.

Design constraints
- Segregation should be achieved **without** a second storage service.
  - Prefer tagging (`artifact_type="plot_image"`) and filtering, rather than separate storage instances.
  - If a physical separation is still desired, prefer a filename/prefix convention or sub-path within the same storage root, but keep the same underlying storage code.
- Alias resolution should not collide with document artifacts.
  - Prefer storing a `plot_alias` in metadata extra fields and resolving it within the plot wrapper.
- Must enforce group ownership on read/list.

Acceptance
- Plot storage behaves like gofr-common storage (same bytes+format return shape), and:
  - image listing only returns `artifact_type="plot_image"`
  - alias resolution works within a group
  - cross-group access is denied

### Step 4 — Add MCP tools to gofr-doc MCP server
Modify gofr-doc MCP server to register **6 new tools** (names can match gofr-plot unless they conflict):
- `plot_ping` or reuse `ping`? (recommended: **do not add** a second ping; reuse gofr-doc `ping`)
- `render_graph`
- `get_image`
- `list_images`
- `list_themes`
- `list_handlers`
- `add_plot_fragment` ← **new** bridge tool (see "Embedding plot images in documents" section above)

Recommendation
- Keep `render_graph/get_image/list_images/list_themes/list_handlers` exact names to preserve gofr-plot client compatibility.
- Do **not** add `token` param. Follow gofr-dig convention and accept `auth_token` as the tool parameter for authenticated tools.

Handler responsibilities
- Parse/validate request via Pydantic (`GraphParams`)
- Validate via GraphDataValidator
- Render via GraphRenderer
- Proxy mode:
  - if `proxy=true`, persist and return a GUID (and alias if provided)
  - else return ImageContent (base64) like gofr-plot
- `add_plot_fragment`:
  - If `plot_guid` provided: fetch stored image from FileStorage → build data URI → add `image_from_url` fragment.
  - If inline render params provided: render in-process → build data URI → add `image_from_url` fragment.
  - Reuses the same `image_from_url` fragment template and session management as `add_image_fragment`.

Acceptance
- `list_tools` shows new tools (including `add_plot_fragment`).
- Rendering returns an `ImageContent` on non-proxy.
- Proxy mode returns a GUID and retrieval works.
- `add_plot_fragment` with `plot_guid` embeds a previously-rendered plot into a document session.
- `add_plot_fragment` with inline params renders and embeds in a single call.

### Step 5 — Port functional MCP tests (gofr-plot → gofr-doc)
Target: add tests under gofr-doc `test/plot_mcp/` (or `test/mcp/` if you want them mixed).

Port these gofr-plot test groups:
- MCP integration tests (live server):
  - `test/mcp/test_mcp_rendering.py`
  - `test/mcp/test_mcp_multi_dataset.py`
  - `test/mcp/test_mcp_axis_controls.py`
  - `test/mcp/test_proxy_mode.py`
  - `test/mcp/test_mcp_handlers.py`
  - `test/mcp/test_mcp_themes.py`
  - `test/mcp/test_mcp_schema.py`

Key adaptations
- Replace `token` argument usage with `auth_token` tool parameter (gofr-dig convention).
- Keep HTTP `Authorization: Bearer` header support as a secondary/backward-compatible path, but tests should exercise the primary `auth_token` parameter path.
- Replace ports/env vars:
  - use gofr-doc’s existing test server ports or the integration harness already used by `test/mcp/*`.
- Update assertions to match gofr-doc response formatting (it uses gofr-common response builder + its own error mapping).

Additional tests for `add_plot_fragment`
- `add_plot_fragment` with `plot_guid` embeds image into a doc session (verify fragment count increases, fragment has `embedded_data_uri`).
- `add_plot_fragment` with inline render params renders and embeds in one call.
- `add_plot_fragment` rejects cross-group `plot_guid` (group isolation).
- `add_plot_fragment` rejects invalid `session_id` (session not found).

Keep / drop
- Drop gofr-plot's "manual_*" tests.
- Keep only tests that validate the 5 graph tools + proxy retrieval + `add_plot_fragment`.

Acceptance
- Plot MCP tests pass alongside existing 571 tests.

### Step 6 — Decide what to do with gofr-plot web tests
gofr-plot includes ASGI-level tests for its FastAPI web server (`POST /render`, `GET /proxy/{guid}`, etc.).

Since the requirement is “tools + functional tests” and gofr-doc web server should remain stable:
- Do **not** port `test/web/test_web_rendering.py` as-is.
- Instead, add a **thin** test that:
  - calls gofr-doc MCP `render_graph(proxy=true)`
  - calls MCP `get_image(identifier=guid)`

If you later want HTTP retrieval for images:
- Add a *new endpoint namespace* (not `/proxy/{...}`), then port the gofr-plot web proxy tests against that.

### Step 7 — Update docs
1. Add plot tools to `docs/tools.md` (new section “Plot Tools”).
2. Add an example snippet to `docs/workflow.md` showing:
   - render_graph (non-proxy)
   - render_graph (proxy) → get_image

Acceptance
- Docs show parameters, proxy mode semantics, and auth requirement.

### Step 8 — Final integration checks
1. Run gofr-doc full test suite.
2. Run minimal “smoke render” against a running MCP container.
3. Ensure no impact to:
   - existing document proxy workflows
   - session lifecycle tools
   - housekeeper

## Pre-merge checklist (to ensure a smooth merge)

### JWT / auth alignment (gofr-doc + gofr-dig pattern)
- Confirm the unified MCP auth pattern matches gofr-dig:
  - Prefer JWT via tool parameter `auth_token` for all authenticated tools.
  - `auth_token` may include a `Bearer ` prefix.
  - Continue supporting gofr-doc’s legacy `{"token": "..."}` **only** for backward compatibility; do not document it as the primary interface.
  - Continue supporting HTTP `Authorization: Bearer <token>` as a secondary path (helpful for some clients), but do not make it the primary pattern.
- Confirm precedence rules match gofr-doc + gofr-dig expectations:
  - If both `auth_token` (or legacy `token`) and `Authorization` header are present, the tool argument wins.
- Confirm multi-group token behavior is consistent:
  - If the JWT contains multiple groups, the first group is used as the primary group for write-scoped actions.
- Confirm plot tools follow gofr-doc’s enforced group boundary:
  - `handle_call_tool()` injects `arguments["group"]` from JWT
  - Plot tool handlers must treat `group` as authoritative and must not trust any client-supplied group
- Confirm tokenless behavior matches existing discovery conventions:
  - Add `list_themes` and `list_handlers` to the token-optional tool set (same pattern as gofr-dig/gofr-doc discovery tools)
  - Keep `render_graph/get_image/list_images` authenticated when auth is enabled

### Vault / secret sourcing (ops remains unchanged)
- Verify production still sources the JWT signing secret the same way as gofr-dig/gofr-doc today (Vault/AppRole via the shared entrypoint).
- Verify no new env prefixes or secret names are required for plot capability (reuse the existing gofr-doc auth configuration).

### Storage boundaries
- Confirm plot proxy artifacts do **not** reuse or overload document proxy storage and do **not** change the meaning of `GET /proxy/{guid}`.
- Confirm group ownership is enforced for image list/retrieval (cross-group reads return not-found/permission-denied behavior consistent with gofr-doc).

### Headless rendering
- Confirm matplotlib renders headless in containers (e.g., Agg backend) and that a basic render succeeds under the same runtime used for production.

### Test gates (must-pass)
- `list_tools` shows `render_graph`, `get_image`, `list_images`, `list_themes`, `list_handlers`, `add_plot_fragment`.
- Non-proxy render returns an MCP `ImageContent`.
- Proxy render returns a GUID and `get_image` returns the persisted image for the same group.
- `add_plot_fragment` with `plot_guid` embeds a stored plot into a document session.
- `add_plot_fragment` with inline render params renders + embeds in one call.
- Full gofr-doc suite passes with plot tests enabled.

## Risk / conflict checklist

- **Endpoint collision:** do not overload gofr-doc `/proxy/{guid}` for images.
- **Dependency weight:** matplotlib can increase image size and runtime; ensure Docker image still builds within acceptable time.
- **Headless rendering:** ensure matplotlib backend works in container (typically Agg works by default).
- **Storage separation:** keep plot image storage separate from document proxy storage.
- **Auth consistency:** enforce group ownership for image retrieval/listing.

## Proposed deliverables (what you should see in the PR)

- New modules: `app/plot/**`
- Updates:
  - gofr-doc MCP server registers 6 plot tools (`render_graph`, `get_image`, `list_images`, `list_themes`, `list_handlers`, `add_plot_fragment`)
  - `pyproject.toml` includes matplotlib + numpy
  - tests added for plot tool functionality (including `add_plot_fragment` integration tests)
  - docs updated

---

If you want, I can execute this plan next: implement the plot modules + tools + tests directly in gofr-doc (keeping the runtime machinery untouched).