# Large File Refactor Specification (No Behavior Change)

## Goal
Reduce cognitive load and improve navigability by splitting a small number of oversized modules into smaller, logically cohesive modules and (where beneficial) collaborator classes.

Hard constraint: this is a refactor only.
- No runtime behavior changes.
- No API/UX changes (tool names, request/response payloads, error codes, and logging semantics remain the same).
- No changes to operational defaults unless explicitly approved.

## Non-goals
- Adding new features, endpoints, tools, options, or configuration.
- Changing authentication / authorization semantics.
- Changing error codes or recovery strategies.
- Large-scale architectural rewrites.

## Hotspots Identified (by line count)
Application code (app/):
- app/mcp_server/mcp_server.py (~2710 lines) - MCP tool schemas, routing, auth injection, tool implementations, server lifecycle.
- app/management/storage_manager.py (~887 lines) - CLI + housekeeper prune logic + storage listing/stats.
- app/web_server/web_server.py (~825 lines) - FastAPI server, auth extraction, images, discovery, render/proxy.
- app/management/render_manager.py (~785 lines) - CLI for discovery/inspection/validation.
- app/sessions/manager.py (~750 lines) - session lifecycle + alias mapping + fragment ops + validation.
- app/validation/table_validator.py (~508 lines) - large Pydantic model with many validators.

This spec focuses on the app/ modules above. (There are also large files under lib/gofr-common and test/, but they are out of scope unless you ask.)

## Design Principles
1. Preserve public entrypoints.
   - Keep the existing top-level scripts/modules importable at their current paths.
   - Prefer turning large files into thin shims that delegate into new submodules.
2. Split by responsibility, not by size.
   - Each new module should have a single reason to change.
3. Minimize churn.
   - Avoid renaming external-facing symbols unless strictly necessary.
   - If internal imports change, use re-exports in __init__.py or a compatibility shim.
4. Improve locality.
   - Keep validation rules near the models they validate.
   - Keep HTTP route definitions near their request/response types.
5. Improve testability without changing tests first.
   - Refactor in small steps where the existing test suite remains green.

## Proposed Refactor 1: Split app/mcp_server/mcp_server.py

### Current responsibilities mixed together
- JSON/text response helpers (_json_text, _success, _error, model dumping)
- Auth extraction + group injection (_verify_auth, TOKEN_OPTIONAL_TOOLS)
- Component initialization (initialize_server and globals)
- Tool schema definition (handle_list_tools)
- Tool implementations for:
  - discovery (templates/styles/fragments)
  - sessions + fragments
  - rendering
  - validation
  - plot subsystem tools
- Tool routing (HANDLERS mapping)
- Server lifecycle (streamable HTTP manager, lifespan, main)

### Target structure (package-level split)
Create submodules under app/mcp_server/ and keep app/mcp_server/mcp_server.py as a thin compatibility shim.

Suggested files (names are negotiable):
- app/mcp_server/responses.py
  - JSON serializer, _json_text, _success, _error
  - validation error formatting (_handle_validation_error)
  - model dumping helper (_model_dump)
- app/mcp_server/auth.py
  - TOKEN_OPTIONAL_TOOLS
  - _verify_auth() and group injection helpers
- app/mcp_server/components.py
  - ServerComponents container (dataclass or simple class) holding registries/managers/renderer/plot components
  - initialize_components() that replaces initialize_server()
  - Small "ensure_*" helpers to avoid global state leaks
- app/mcp_server/tool_schemas.py
  - handle_list_tools() implementation only
  - Keep schemas together, ideally grouped by domain (discovery/session/render/plot)
- app/mcp_server/tools/
  - discovery.py (ping, help, list_templates, get_template_details, list_template_fragments, get_fragment_details, list_styles)
  - sessions.py (create_document_session, get_session_status, list_active_sessions, abort_document_session)
  - fragments.py (set_global_parameters, add_fragment, add_image_fragment, remove_fragment, list_session_fragments)
  - rendering.py (get_document)
  - validation.py (validate_parameters)
  - plot.py (render_graph, get_image, list_images, list_themes, list_handlers, add_plot_fragment)
- app/mcp_server/routing.py
  - HANDLERS mapping (assembled from tools/*)
  - handle_call_tool() implementation
- app/mcp_server/server.py
  - streamable HTTP integration, lifespan wiring, starlette app creation, main()

Compatibility shim:
- app/mcp_server/mcp_server.py stays as the import path used by existing entrypoints.
  - It imports and re-exports what is needed and delegates main lifecycle hooks.
  - This keeps external callers (and any scripts) stable.

### Optional (behavior-preserving) de-duplication
Today many tool handlers repeat the same "resolve alias -> load session -> verify group" pattern.
A single helper can centralize that logic while preserving:
- error codes
- error messages
- recovery strings

Example concept (no code here): require_session_in_group(session_identifier, group) -> (session_id, session) or a ToolResponse error.

This reduces the likelihood of drift between tools while keeping semantics consistent.

### Acceptance criteria
- All existing MCP tools behave the same (schemas, required fields, error codes, and response shapes).
- Full test suite passes.

## Proposed Refactor 2: Split app/web_server/web_server.py

### Current responsibilities mixed together
- FastAPI app construction and route registration
- Auth header parsing / group extraction
- Stock image directory traversal protection and serving
- Discovery endpoints + render/proxy endpoints

### Target structure
Keep GofrDocWebServer as the public class, but move helper responsibilities into small modules:
- app/web_server/auth.py
  - parse headers, group extraction, auth-required checks
- app/web_server/images.py
  - path resolution, extension/mime allowlist, response helpers
- app/web_server/routes_discovery.py
  - templates/fragments/styles endpoints
- app/web_server/routes_render.py
  - render/proxy endpoints
- app/web_server/app_factory.py (optional)
  - constructs FastAPI and wires routes into the server class

The goal is that web_server.py becomes a thin orchestrator and routing entrypoint.

### Acceptance criteria
- Endpoint paths, request/response payloads, and status codes remain identical.
- Image traversal protections remain identical.
- Full test suite passes.

## Proposed Refactor 3: Split management CLIs (storage_manager.py, render_manager.py)

### Current responsibilities mixed together
- Argument parsing
- Directory resolution logic duplicated across scripts
- Multiple subcommands implemented as large functions
- Housekeeper-oriented logic embedded in the same script

### Target structure
Create a small CLI package under app/management/cli/:
- app/management/cli/common_paths.py
  - shared resolve_*_dir helpers (templates, fragments, styles, storage)
- app/management/cli/storage_commands.py
  - purge_documents, list_documents, stats, prune_size and lock helpers
- app/management/cli/render_commands.py
  - list_templates, get_template_details, list_template_fragments, etc.
- app/management/storage_manager.py and app/management/render_manager.py remain as thin entrypoints
  - they parse args and delegate to the appropriate command function

This keeps the scripts stable while making the command implementations navigable.

### Acceptance criteria
- CLI arguments and outputs remain identical (including exit codes).
- Housekeeper prune lock behavior remains identical.
- Full test suite passes.

## Proposed Refactor 4: Split app/sessions/manager.py

### Current responsibilities mixed together
- Alias management (bidirectional mapping + loading existing aliases)
- Session lifecycle (create/get/abort)
- Session mutation (globals/fragments)
- Session validation for render (readiness checks)

### Target structure
Keep SessionManager as the public facade class (to avoid widespread call site churn), but delegate to collaborators:
- app/sessions/aliases.py
  - AliasRegistry: load aliases from SessionStore, register/unregister, resolve alias->guid
- app/sessions/lifecycle.py
  - SessionLifecycle: create_session, abort_session, get_session
- app/sessions/mutations.py
  - SessionMutator: set_global_parameters, add_fragment, remove_fragment
- app/sessions/validation.py
  - SessionReadinessValidator: validate_session_for_render, validate_parameters

SessionManager composes these, keeping its existing method signatures and semantics.

### Acceptance criteria
- All SessionManager methods behave the same.
- Existing MCP tools continue returning the same errors/messages.
- Full test suite passes.

## Proposed Refactor 5: Split app/validation/table_validator.py

### Current responsibilities mixed together
- Pydantic model
- Structural constraints (rows non-empty, consistent column counts)
- Parameter constraints (width/border/alignments)
- Cross-field validation (sort_by, column widths, highlight indices)
- Delegation into number-format and color validators

### Target structure
Keep TableData as the external model, but move rule groups into small modules to reduce the "wall of validators":
- app/validation/table_models.py
  - TableData model definition + minimal field typing
- app/validation/table_rules_structure.py
  - rows non-empty, consistent column counts
- app/validation/table_rules_formatting.py
  - number_format specs, alignment/border/width parsing
- app/validation/table_rules_highlights.py
  - highlight rows/cols range checks
- app/validation/table_rules_sorting.py
  - sort_by validation

This can be done either by:
- calling shared functions inside validators, or
- using a small internal "rules engine" invoked by a single model_validator.

### Acceptance criteria
- Same exceptions and error codes for the same invalid inputs.
- Full test suite passes.

## Sequencing (Recommended)
1. mcp_server split first (highest value, largest file, most duplicated patterns).
2. sessions split next (enables cleaner MCP handler code without changing semantics).
3. web_server split (purely for navigability; ensure no API drift).
4. management CLI split.
5. table_validator split.

Each step should land independently with tests passing to reduce risk.

## Risks and Mitigations
- Risk: subtle behavior drift when moving code (imports, globals, exception mapping).
  - Mitigation: small steps, keep compatibility shims, run full test suite after each step.
- Risk: circular imports after splitting.
  - Mitigation: define low-level modules first (responses/auth/components), then tools, then routing/server.
- Risk: refactor touches too many call sites.
  - Mitigation: keep facades (SessionManager, GofrDocWebServer) and keep original module entrypoints as shims.

## Assumptions (Please Confirm)
A1. It is acceptable to change internal import paths within the repo to improve navigability.
A2. Compatibility shims / re-exports are allowed, but we should prefer fewer layers when simplicity improves.
A3. We can add small internal helper classes (facades/collaborators) as long as runtime behavior stays the same and tests pass.
A4. Passing the full test suite via ./scripts/run_tests.sh is the acceptance gate for each refactor step.

## Decisions Confirmed (2026-02-17)
D1. Prioritization: start with the largest and hardest-to-navigate modules, beginning with app/mcp_server/mcp_server.py.
D2. "No functions should change" means behavior should remain stable and tests should pass; code changes are fine.
D3. Re-exports/shims are acceptable, but import-path changes are also acceptable if they reduce overall complexity.
D4. No target maximum file size; the acid test is simple navigation and supportability.
