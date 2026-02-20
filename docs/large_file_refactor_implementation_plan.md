# Large File Refactor - Implementation Plan (Phase 2)

## Scope
Primary: split the largest hotspot module to improve navigability while preserving behavior.
- app/mcp_server/mcp_server.py (~2710 lines)

Secondary (later phases, separate approvals if desired):
- app/sessions/manager.py
- app/web_server/web_server.py
- app/management/storage_manager.py
- app/management/render_manager.py
- app/validation/table_validator.py

## Non-negotiables
- Refactor only: no behavior changes.
- Preserve tool schemas, tool names, error codes, and response shapes.
- Full suite must pass before and after via ./scripts/run_tests.sh.
- No new UX/API surface.

## Execution Strategy
Split by responsibility into small modules with a clear dependency direction:
- Lowest-level utilities first (responses, auth helpers)
- Component wiring next (initialization + ensure helpers)
- Tool handlers grouped by domain next
- Routing and server lifecycle last

Prefer simplifying imports over adding shims. Keep a shim only where an entrypoint depends on it.

## Step-by-step Plan

### Step 0 - Baseline
0.1 Run full test suite (baseline).
- Command: ./scripts/run_tests.sh
- Record results. If failures exist, stop and discuss whether to fix baseline first or proceed with known failures.

Status: DONE (2026-02-17) - 709 passed.

### Step 1 - Establish module skeleton for MCP server
1.1 Create new modules under app/mcp_server/:
- responses.py
- auth.py
- components.py
- tool_schemas.py
- routing.py
- server.py
- tools/ (package)
  - __init__.py
  - discovery.py
  - sessions.py
  - fragments.py
  - rendering.py
  - validation.py
  - plot.py

1.2 Verify imports resolve (static check).
- Run: ./scripts/run_tests.sh -k "code_quality" (or the existing code quality subset if supported)
- Goal: catch obvious import/cycle problems early.

Status: DONE (2026-02-17) - module skeleton created; code-quality tests passed.

### Step 2 - Extract response helpers (no behavior change)
2.1 Move the following helpers into responses.py (names preserved):
- _json_serializer
- _json_text
- _success
- _error
- _handle_validation_error
- _model_dump

2.2 Update mcp_server.py (and later modules) to import these helpers.

2.3 Verify with a targeted test run:
- ./scripts/run_tests.sh -k "test_ping or test_error_handling" (adjust keyword to match existing tests)

Status: DONE (2026-02-17) - extracted helpers to app/mcp_server/responses.py; targeted tests passed.

### Step 3 - Extract auth helpers
3.1 Move auth-related logic into auth.py:
- TOKEN_OPTIONAL_TOOLS
- _verify_auth
- Any small helper(s) needed for token extraction rules

3.2 Update call routing to use extracted auth.

3.3 Verify targeted tests:
- ./scripts/run_tests.sh -k "mcp and (auth or group_security)" (adjust keyword as needed)

Status: DONE (2026-02-17) - extracted auth helpers to app/mcp_server/auth.py; targeted tests passed.

### Step 4 - Extract component initialization and ensure helpers
4.1 Create a ServerComponents container (dataclass or simple class) in components.py to hold:
- TemplateRegistry, StyleRegistry
- SessionStore, SessionManager
- RenderingEngine
- Plot renderer, storage wrapper, validator

4.2 Move initialize_server logic into components.py as initialize_components (same behavior):
- Preserve override handling (templates_dir_override, styles_dir_override)
- Preserve web_url_override and proxy_url_mode usage

4.3 Replace global variables with a single module-level components instance where practical.
- Keep behavior identical (lifecycle, initialization order, defaults)

4.4 Verify targeted tests:
- ./scripts/run_tests.sh -k "mcp and session_lifecycle"

Status: DONE (2026-02-17) - introduced ServerComponents + initialize_components; targeted tests passed.

### Step 5 - Split tool schema definitions
5.1 Move handle_list_tools implementation into tool_schemas.py.
- Keep schemas byte-for-byte equivalent where feasible (descriptions and inputSchema).
- Keep tool names identical.

5.2 Re-export handle_list_tools from the current entry module if needed.

5.3 Verify targeted tests:
- ./scripts/run_tests.sh -k "document_discovery"

Status: DONE (2026-02-18) - moved tool schemas into app/mcp_server/tool_schemas.py; discovery + code-quality tests passed.

### Step 6 - Split tool handlers by domain
6.1 Move tool handler functions into app/mcp_server/tools/*:
- discovery.py: _tool_ping, _tool_help, _tool_list_templates, _tool_get_template_details, _tool_list_template_fragments, _tool_get_fragment_details, _tool_list_styles
- sessions.py: _tool_create_session, _tool_get_session_status, _tool_list_active_sessions, _tool_abort_session
- fragments.py: _tool_set_global_parameters, _tool_add_fragment, _tool_add_image_fragment, _tool_remove_fragment, _tool_list_session_fragments
- rendering.py: _tool_get_document
- validation.py: _tool_validate_parameters
- plot.py: _tool_render_graph, _tool_get_image, _tool_list_images, _tool_list_themes, _tool_list_handlers, _tool_add_plot_fragment

6.2 Keep helper _resolve_session_identifier either:
- in a small shared module (e.g., tools/common.py), or
- in sessions.py and imported by fragments/rendering as needed.

6.3 Verify targeted tests (run a few focused keywords, one at a time):
- ./scripts/run_tests.sh -k "fragment_management"
- ./scripts/run_tests.sh -k "image_fragment"
- ./scripts/run_tests.sh -k "proxy_rendering"
- ./scripts/run_tests.sh -k "plot"

Status: DONE (2026-02-18) - moved tool handlers into app/mcp_server/tools/*; ./scripts/run_tests.sh -k "code_quality" and ./scripts/run_tests.sh -k "mcp" passed.

### Step 7 - Centralize routing
7.1 Build HANDLERS mapping in routing.py by importing tool functions from tools/*.

7.2 Move handle_call_tool to routing.py.
- Preserve:
  - logging fields
  - auth injection semantics (group injection)
  - error mapping via map_error_for_mcp
  - error codes and payload structure

7.3 Verify targeted tests:
- ./scripts/run_tests.sh -k "mcp"

Status: DONE (2026-02-18) - moved HANDLERS mapping and dispatch logic into app/mcp_server/routing.py; ./scripts/run_tests.sh -k "code_quality" and ./scripts/run_tests.sh -k "mcp" passed.

### Step 8 - Centralize server lifecycle wiring
8.1 Move streamable HTTP wiring and lifespan into server.py.
- Preserve StreamableHTTPSessionManager config.
- Preserve Starlette app creation via gofr_common.web.
- Preserve main(host, port) behavior.

8.2 Make app/mcp_server/mcp_server.py a small entry module.
- Minimal re-exports only if needed by other modules.

8.3 Verify targeted tests:
- ./scripts/run_tests.sh -k "test_ping"

Status: DONE (2026-02-18) - moved StreamableHTTP wiring + lifespan + Starlette app creation into app/mcp_server/server.py; updated app/main_mcp.py entrypoint; ./scripts/run_tests.sh -k "code_quality" and ./scripts/run_tests.sh -k "mcp" passed.

### Step 9 - Acceptance
9.1 Run full test suite (acceptance).
- Command: ./scripts/run_tests.sh

9.2 If any failures:
- Fix regressions introduced by refactor.
- Do not change external behavior to “make tests pass”; preserve semantics.

Status: DONE (2026-02-18) - full suite passed: 709 passed.

## Definition of Done
- app/mcp_server/mcp_server.py is no longer a monolith and is easy to navigate.
- Clear module boundaries exist (responses/auth/components/schemas/tools/routing/server).
- Full test suite passes before and after refactor.

## Notes
- If circular imports appear, adjust dependency direction (tools should depend on components/auth/responses, not the reverse).
- Keep changes small per step; avoid moving unrelated code.
