# Document Generation MCP Service Specification

## 1. Project Overview

- **Objective**: Deliver a stateful, discoverable, and type-safe Document Generation API with group-based multi-tenant security, exposed to agentic LLM clients via the Model Context Protocol (MCP).
- **Workflow**: LLM follows a Think → Act → Observe loop across discovery, session management, iterative content assembly, rendering, and explicit cleanup, all within a secure group context.
- **Quality Goals**: Minimal, production-ready async Python with strong validation, multi-tenant isolation, maintainability, performance, observability, and persistence across restarts.
- **Context**: Replaces the earlier graph MCP server while retaining shared subsystems (auth, storage, logging) and introducing document-centric components with group-based security.

## 2. Technology Stack & Architecture

| Component | Technology | Notes |
|-----------|------------|-------|
| Protocol | `mcp>=0.9.0` | Primary integration surface for LLM agents |
| Web Framework | FastAPI (async) | Hosts MCP transport endpoints with minimal glue |
| Validation | Pydantic v2 | Universal schema enforcement for inputs/outputs |
| Templates | Pydantic schema + Jinja2 rendering | Type-safe parameters with flexible HTML templating |
| Styles | HTML + CSS (Jinja2 + static CSS files) | Stylesheet layer independent of template structure |
| Rendering | HTML base → WeasyPrint (PDF) → html2text (Markdown) | HTML is canonical representation |
| Storage | Existing persistent storage (`app/storage`) | Sessions survive process restarts; group-scoped directories |
| Logging | Existing structured logger (`app/logger`) | Consistent, contextual diagnostics |
| Auth | JWT with group claims | Multi-tenant isolation via group extraction from token |
| Security | Group-based access control | Session ownership verification, directory isolation per group |

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

1. **Create**: `create_document_session` locks template for the session and binds it to the caller's group.
2. **Iterate**: `set_global_parameters` (overwritable), `add_fragment`, `remove_fragment`, `list_session_fragments`—all verified against session ownership.
3. **Render**: `get_document` supports repeated renders (`html`, `pdf`, `md`) with optional style selection; must follow successful `set_global_parameters`.
4. **Cleanup**: `abort_document_session` deletes session data from persistent storage and validates group ownership.

### Persistence & Security

- Sessions stored with key prefix `session:<group>:<uuid>` via `app/storage` and persist across restarts.
- Each session is bound to a group extracted from the JWT token's `group` claim.
- Fragment GUIDs scoped to their session, automatically cleaned on abort.
- Session metadata records creation, update timestamps, and group context for observability and enforcement.
- All session operations verify caller's group matches session's group; cross-group access is denied with `SESSION_NOT_FOUND`.
- In non-authentication mode (development), all sessions default to the `public` group.

### Concurrency & Access

- Async session manager enables concurrent operations while relying on storage guarantees.
- Multiple agents may coordinate on a session using fragment GUIDs for deterministic updates.
- Group isolation prevents accidental or malicious cross-tenant access.

## 6. Security Model

### Authentication & Group Binding

- **JWT Tokens**: Clients provide JWT tokens via HTTP `Authorization: Bearer <token>` header in MCP server mode, or via environment configuration in development.
- **Group Extraction**: On each request, the auth service extracts the `group` claim from the JWT payload.
- **Session Ownership**: Sessions are created with and bound to the caller's group. All subsequent operations (`set_global_parameters`, `add_fragment`, `remove_fragment`, `list_session_fragments`, `get_document`, `abort_document_session`) verify that the caller's group matches the session's group.
- **Access Denial**: If group mismatch detected, the session is treated as non-existent (`SESSION_NOT_FOUND`), preventing information leakage.

### Non-Authentication Mode

- **Development Workflow**: When authentication is disabled (no `DOCO_AUTH_SERVICE_URL` or equivalent), all operations default to the `public` group.
- **Use Case**: Local development, testing, and single-tenant deployments without auth infrastructure.
- **Behavior**: Discovery tools (templates, styles) remain unrestricted; all sessions created default to `public` and are accessible only in non-auth context.

### Directory Isolation

- **Storage**: Group context is encoded in storage key prefixes (`session:<group>:<uuid>`, etc.), enabling future per-group filesystem isolation.
- **Data**: Sessions and artifacts (fragments, rendered documents) are logically partitioned by group and inaccessible to other groups.

## 7. Tool Surface (Source of Truth)

## 7. Tool Surface (Source of Truth)

```text
# Discovery Tools (no authentication required)
ping
list_templates
get_template_details
list_template_fragments
get_fragment_details
list_styles

# Session Tools (require valid JWT with group claim or no-auth mode)
create_document_session       # Binds session to caller's group
set_global_parameters        # Verifies session ownership
add_fragment                  # Verifies session ownership
remove_fragment               # Verifies session ownership
list_session_fragments        # Verifies session ownership
abort_document_session        # Verifies session ownership
get_document                  # Verifies session ownership
```

- `add_fragment` returns `fragment_instance_guid`, insertion index, and confirmation message.
- `get_document` enforces prior global parameter configuration while leaving session active for subsequent renders.
- All session tools validate `session.group == caller.group` before proceeding.
- Pydantic models mirror tool I/O schemas to ensure precise validation and documentation.

## 8. Error Handling & Recovery Guidance

- **MCP Responses**: Structured `ErrorResponse` with `error_code`, `message`, contextual `details`, and actionable `recovery_strategy`.
- **Web API**: HTTP status codes plus mirrored descriptive payloads for human operators.
- **Validation Coverage**: Missing/extra parameters, invalid IDs, ordering references to unknown GUIDs, unset global parameters on render, unsupported formats or styles, cross-group access attempts.
- **Security Errors**: Mismatched group claims return `SESSION_NOT_FOUND` (rather than explicit "access denied") to prevent information leakage.
- **Example Strategy**: "Call set_global_parameters with required fields before invoking get_document" or "Ensure your JWT token contains a valid 'group' claim."

## 9. Rendering Pipeline

1. **HTML Generation**: Template registry renders `document.html.jinja2`, injecting global parameters, ordered fragment HTML, and CSS references.
2. **PDF Conversion**: WeasyPrint converts HTML to PDF, returning base64-encoded data for transport.
3. **Markdown Conversion**: html2text translates HTML to Markdown with preserved links, images, and unclamped line widths.

## 10. Reuse & Integration Plan

- **Reuse**: `auth`, `storage`, `logger`, `config` modules remain intact.
- **Replace/Update**: `app/mcp_server.py` and related entry points transition to document tooling.
- **New Components**: Template/style registries, session manager, rendering engine, expanded validation schemas.
- **Testing**: End-to-end flow tests plus targeted validation/error-path coverage; persistence validated through restart scenarios.

## 11. Resolved Design Decisions

- ✅ Hybrid Pydantic schema + Jinja2 templating for templates.
- ✅ UUID4 fragment instance GUIDs returned by `add_fragment`.
- ✅ Dedicated `list_session_fragments` and `remove_fragment` tools.
- ✅ HTML as canonical format, with WeasyPrint (PDF) and html2text (Markdown) conversions.
- ✅ Styles defined independently via CSS bundles.
- ✅ Readable slugs for templates/fragments/styles; UUID4 for sessions/fragment instances.
- ✅ Descriptive MCP errors with recovery actions; HTTP responses for web surface.
- ✅ Sessions persisted via existing storage service.
- ✅ **Group-based multi-tenant security**: Sessions bound to JWT group claim with cross-group access denial.
- ✅ **Dual-mode operation**: Production auth mode (JWT with groups) and development no-auth mode (public group default).

## 12. Implementation Roadmap

1. Implement MCP tool handlers leveraging new registries, session manager, and rendering engine, with group-based security verification.
2. Populate initial templates (e.g., `basic_report`, `technical_doc`) and styles.
3. Develop automated tests spanning discovery → session → construction → rendering → cleanup, including multi-tenant security and group isolation validation.
4. Refresh documentation in `docs/` and related run-books.
5. Verify deployment scripts and Docker assets for new dependencies (Jinja2, WeasyPrint, html2text, PyYAML).

---

**Status**: Specification finalized and updated (Nov 18, 2025) with group-based security model. Core implementation complete with 300/300 tests passing, including 5 security tests and 4 end-to-end workflow tests demonstrating full multi-tenant isolation.
