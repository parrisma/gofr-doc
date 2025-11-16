# Document Generation MCP Service Specification

## 1. Project Overview

- **Objective**: Deliver a stateful, discoverable, and type-safe Document Generation API, exposed to agentic LLM clients via the Model Context Protocol (MCP).
- **Workflow**: LLM follows a Think → Act → Observe loop across discovery, session management, iterative content assembly, rendering, and explicit cleanup.
- **Quality Goals**: Minimal, production-ready async Python with strong validation, maintainability, performance, observability, and persistence across restarts.
- **Context**: Replaces the earlier graph MCP server while retaining shared subsystems (auth, storage, logging) and introducing document-centric components.

## 2. Technology Stack & Architecture

| Component | Technology | Notes |
|-----------|------------|-------|
| Protocol | `mcp>=0.9.0` | Primary integration surface for LLM agents |
| Web Framework | FastAPI (async) | Hosts MCP transport endpoints with minimal glue |
| Validation | Pydantic v2 | Universal schema enforcement for inputs/outputs |
| Templates | Pydantic schema + Jinja2 rendering | Type-safe parameters with flexible HTML templating |
| Styles | HTML + CSS (Jinja2 + static CSS files) | Stylesheet layer independent of template structure |
| Rendering | HTML base → WeasyPrint (PDF) → html2text (Markdown) | HTML is canonical representation |
| Storage | Existing persistent storage (`app/storage`) | Sessions survive process restarts |
| Logging | Existing structured logger (`app/logger`) | Consistent, contextual diagnostics |
| Auth | Existing auth module | Shared JWT validation across surfaces |

### Key Directories

```text
app/
  templates/        # Template registry + loaders
  styles/           # Style registry and CSS helpers
  fragments/        # Fragment helper utilities (reserved)
  sessions/         # Session manager and persistence logic
  rendering/        # Rendering engine and converters
  validation/       # Pydantic schemas and validation helpers
templates/          # Static template bundles (YAML + Jinja2)
styles/             # Static style bundles (style.yaml + style.css)
```

## 3. Template & Fragment System

- **Definition Approach**: `TemplateSchema` (Pydantic) captures metadata, global parameters, and fragment schemas; YAML files provide data, Jinja2 renders HTML.
- **Structure Example**: `templates/basic_report/{template.yaml, document.html.jinja2, fragments/paragraph.html.jinja2}`.
- **Parameter Types**: Enumerated (`string`, `integer`, `number`, `boolean`, `array`, `object`) with descriptions, required flags, defaults, and examples.
- **Fragment Instances**: `add_fragment` generates UUID4 `fragment_instance_guid`, persisted with parameters and timestamps.
- **Ordering**: Fragments append by default; `position` supports `start`, `end`, `before:<guid>`, or `after:<guid>`.
- **Removal**: `remove_fragment` deletes a fragment instance; all fragment GUIDs purged on session abort.
- **Inspection**: `list_session_fragments` reveals ordered fragment metadata for LLM observability and re-planning.

## 4. Style System

- **Independence**: Styles parallel CSS—decoupled from templates, linked by shared element names.
- **Assets**: Each style bundle contains `style.yaml` (metadata) and `style.css` (complete stylesheet).
- **Defaults**: First successfully loaded style becomes default; callers may override via `style_id` during render.
- **Reuse**: Styles apply uniformly across HTML, PDF, and Markdown outputs.

## 5. Session Lifecycle & Persistence

1. **Create**: `create_document_session` locks template for the session.
2. **Iterate**: `set_global_parameters` (overwritable), `add_fragment`, `remove_fragment`, `list_session_fragments`.
3. **Render**: `get_document` supports repeated renders (`html`, `pdf`, `md`) with optional style selection; must follow successful `set_global_parameters`.
4. **Cleanup**: `abort_document_session` deletes session data from persistent storage.

### Persistence

- Sessions stored with key prefix `session:<uuid>` via `app/storage` and persist across restarts.
- Fragment GUIDs scoped to their session, automatically cleaned on abort.
- Session metadata records creation and update timestamps for observability and future lifecycle policies.

### Concurrency & Access

- Async session manager enables concurrent operations while relying on storage guarantees.
- Multiple agents may coordinate on a session using fragment GUIDs for deterministic updates.

## 6. Tool Surface (Source of Truth)

```text
ping
list_templates
get_template_details
list_template_fragments
get_fragment_details
list_styles
create_document_session
set_global_parameters
add_fragment
remove_fragment
list_session_fragments
abort_document_session
get_document
```

- `add_fragment` returns `fragment_instance_guid`, insertion index, and confirmation message.
- `get_document` enforces prior global parameter configuration while leaving session active for subsequent renders.
- Pydantic models mirror tool I/O schemas to ensure precise validation and documentation.

## 7. Error Handling & Recovery Guidance

- **MCP Responses**: Structured `ErrorResponse` with `error_code`, `message`, contextual `details`, and actionable `recovery_strategy`.
- **Web API**: HTTP status codes plus mirrored descriptive payloads for human operators.
- **Validation Coverage**: Missing/extra parameters, invalid IDs, ordering references to unknown GUIDs, unset global parameters on render, unsupported formats or styles.
- **Example Strategy**: "Call set_global_parameters with required fields before invoking get_document."

## 8. Rendering Pipeline

1. **HTML Generation**: Template registry renders `document.html.jinja2`, injecting global parameters, ordered fragment HTML, and CSS references.
2. **PDF Conversion**: WeasyPrint converts HTML to PDF, returning base64-encoded data for transport.
3. **Markdown Conversion**: html2text translates HTML to Markdown with preserved links, images, and unclamped line widths.

## 9. Reuse & Integration Plan

- **Reuse**: `auth`, `storage`, `logger`, `config` modules remain intact.
- **Replace/Update**: `app/mcp_server.py` and related entry points transition to document tooling.
- **New Components**: Template/style registries, session manager, rendering engine, expanded validation schemas.
- **Testing**: End-to-end flow tests plus targeted validation/error-path coverage; persistence validated through restart scenarios.

## 10. Resolved Design Decisions

- ✅ Hybrid Pydantic schema + Jinja2 templating for templates.
- ✅ UUID4 fragment instance GUIDs returned by `add_fragment`.
- ✅ Dedicated `list_session_fragments` and `remove_fragment` tools.
- ✅ HTML as canonical format, with WeasyPrint (PDF) and html2text (Markdown) conversions.
- ✅ Styles defined independently via CSS bundles.
- ✅ Readable slugs for templates/fragments/styles; UUID4 for sessions/fragment instances.
- ✅ Descriptive MCP errors with recovery actions; HTTP responses for web surface.
- ✅ Sessions persisted via existing storage service.

## 11. Implementation Roadmap

1. Implement MCP tool handlers leveraging new registries, session manager, and rendering engine.
2. Populate initial templates (e.g., `basic_report`, `technical_doc`) and styles.
3. Develop automated tests spanning discovery → session → construction → rendering → cleanup.
4. Refresh documentation in `docs/` and related run-books.
5. Verify deployment scripts and Docker assets for new dependencies (Jinja2, WeasyPrint, html2text, PyYAML).

---

**Status**: Specification finalized (Nov 13, 2025) and ready for implementation.
