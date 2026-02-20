# Large File Refactor Alignment Report

Date: 2026-02-18

This report reviews the current codebase against the goals and target structures in `docs/large_file_refactor_spec.md`.

Scope in spec:
- app/mcp_server/mcp_server.py
- app/web_server/web_server.py
- app/management/storage_manager.py
- app/management/render_manager.py
- app/sessions/manager.py
- app/validation/table_validator.py

Out of scope:
- lib/gofr-common and test/ changes unless directly relevant to alignment

## Executive Summary

The refactor goals are partially achieved.

- The MCP server split has been executed and is broadly aligned with the spec: the legacy `app/mcp_server/mcp_server.py` is now a thin shim (~75 lines), with responsibilities moved into focused modules (auth, responses, routing, components, server lifecycle) and domain tool modules under `app/mcp_server/tools/`.
- The other large hotspots called out in the spec (web server, management CLIs, session manager, table validator) remain largely as single large modules with mixed responsibilities. They match the pre-refactor state described in the spec and still represent the largest navigability / cognitive-load risks.
- Tests exist with significant coverage around MCP, web, session lifecycle, and table validation, which is a strong enabler for further refactor steps without behavior drift.

Net: the codebase is moving in the right direction, but only the MCP portion matches the intended target structure so far.

## Repository Observations Relevant to Maintenance

Top-level package structure in `app/` already aligns well with domain boundaries:
- `templates/`, `styles/`, `fragments/`, `sessions/`, `rendering/`, `validation/`, `mcp_server/`, `web_server/`, `management/`, `plot/`.

This is a good baseline for maintainability, because further refactors can be implemented as internal splits while keeping stable facades.

Line-count hotspots (current, app/ only):
- `app/mcp_server/tool_schemas.py` ~951 lines (still large)
- `app/management/storage_manager.py` ~886 lines
- `app/web_server/web_server.py` ~824 lines
- `app/management/render_manager.py` ~785 lines
- `app/sessions/manager.py` ~750 lines
- `app/validation/table_validator.py` ~507 lines

Note: `app/mcp_server/mcp_server.py` is now ~75 lines (refactor success).

## Alignment vs Spec: MCP Server

Spec target: split `app/mcp_server/mcp_server.py` into responses/auth/components/tool_schemas/tools/*/routing/server with a compatibility shim.

Current state: aligned.

### What matches the spec closely

1) Thin compatibility shim
- `app/mcp_server/mcp_server.py` is now a thin entrypoint that wires MCP decorators to:
  - `initialize_components()` in `app/mcp_server/components.py`
  - `build_tools()` in `app/mcp_server/tool_schemas.py`
  - dispatch via `app/mcp_server/routing.py`

This matches the “preserve public entrypoints” and “thin shim delegating into submodules” principle.

2) Separation of concerns into focused modules
- `app/mcp_server/components.py` (init + dependency wiring)
- `app/mcp_server/auth.py` (token optional tools set + verify_auth)
- `app/mcp_server/responses.py` (response formatting + validation error formatting)
- `app/mcp_server/routing.py` (HANDLERS mapping + dispatch_tool_call)
- `app/mcp_server/server.py` (StreamableHTTP lifecycle + Starlette wiring + main)

This is close to the spec’s suggested names and responsibilities.

3) Tool implementations split by domain
- `app/mcp_server/tools/discovery.py`
- `app/mcp_server/tools/sessions.py`
- `app/mcp_server/tools/fragments.py`
- `app/mcp_server/tools/rendering.py`
- `app/mcp_server/tools/validation.py`
- `app/mcp_server/tools/plot.py`

This aligns with “split by responsibility, not by size” and improves locality.

4) Behavior-preserving intent is explicitly stated
Multiple modules include an explicit “Behavior must remain identical…” statement in module docstrings. This is good for reviewers and reduces the chance a refactor PR becomes a feature PR.

### Remaining maintenance issues inside MCP server

1) `tool_schemas.py` remains very large
- The schema isolation is useful (keeps entrypoint small), but 951 lines of literal schema objects is still a navigability hotspot.
- This is acceptable as a single responsibility module, but it still produces cognitive load and makes merges more conflict-prone.

Alignment: partially aligned. The spec wanted `tool_schemas.py`, but also suggested grouping by domain. The current file likely needs explicit internal structure (domain builder helpers, or per-domain schema lists) to be “easy to navigate”.

2) Session resolution / security checks are still duplicated across tools
There is a shared helper `resolve_session_identifier()` in `app/mcp_server/tools/common.py`, but tool handlers still repeat:
- resolve identifier
- if missing -> SESSION_NOT_FOUND
- load session
- verify session.group == caller_group
- if mismatch -> SESSION_NOT_FOUND

This is exactly the spec’s “optional de-duplication” area. Today it is still duplicated and therefore a drift risk.

3) Global server state
- `app/mcp_server/state.py` keeps a global `components` variable and provides `ensure_*` accessors.

This is not necessarily wrong for a service entrypoint, but it is a maintenance hazard:
- makes dependency boundaries implicit
- makes unit testing tool handlers harder

Spec alignment: acceptable given “minimize churn” and compatibility, but it is a long-term improvement target.

## Alignment vs Spec: Web Server

Spec target: split `app/web_server/web_server.py` into auth/images/routes_discovery/routes_render with `GofrDocWebServer` preserved.

Current state: not yet aligned.

Evidence:
- One class `GofrDocWebServer` owns auth parsing, image resolution, and route wiring via nested route functions.
- Method list suggests multiple responsibilities:
  - `_extract_auth_group`, `_verify_auth_header`
  - `_resolve_image_path`, `_content_type_for`
  - `_setup_routes` defines many endpoints (ping, discovery endpoints, images, get_document, proxy)

Maintenance impact:
- Large nested route definitions are difficult to test in isolation.
- A change in auth logic can inadvertently impact unrelated routes.
- This file is likely to grow if any new endpoint is added.

## Alignment vs Spec: Management CLIs (storage_manager, render_manager)

Spec target: extract command implementations and shared path resolution under `app/management/cli/*` and keep entrypoints thin.

Current state: not yet aligned.

What is good:
- Both scripts have clear module-level docstrings.
- There is an attempt to centralize “resolve_*_dir” functions at the top of each file.

What is misaligned / hard to maintain:
- Directory resolution helpers are duplicated across scripts (templates/styles/fragments in render_manager; storage/sessions in storage_manager).
- Each file mixes:
  - arg parsing
  - core business logic
  - filesystem operations / locking
  - output formatting

Maintenance impact:
- Refactors are higher risk because output formatting, exit codes, and command semantics are intertwined.
- Reuse is limited; adding a third CLI will likely duplicate even more logic.

## Alignment vs Spec: Session Manager

Spec target: keep `SessionManager` as facade but split into collaborators (aliases, lifecycle, mutations, validation).

Current state: not yet aligned.

Evidence:
- `SessionManager` class contains all responsibilities:
  - alias loading/validation/registration
  - create/get/abort session
  - set globals, add/remove fragments, list fragments
  - readiness validation and parameter validation

Maintenance impact:
- Cross-cutting changes (e.g., alias behavior, validation rules) require touching a very large class.
- The class likely forces internal coupling between alias storage format and session lifecycle.

Positive note:
- There are clear internal helper methods already, which will make extraction into collaborators straightforward without API changes.

## Alignment vs Spec: Table Validator

Spec target: split `table_validator.py` into model + rule modules (structure/formatting/highlights/sorting), keeping `TableData` as external model.

Current state: partially aligned (at the package level), but not aligned for this file.

Evidence:
- `table_validator.py` still contains:
  - `TableData` model
  - many validators that span multiple concern areas
  - a wrapper `validate_table_data()`

What does align:
- The broader validation package already has some decomposition:
  - `app/validation/color_validator.py`
  - `app/validation/image_validator.py`
  - `app/validation/models/*` (inputs/outputs/schema/session)

Maintenance impact:
- The “wall of validators” still exists, so this remains a cognitive hotspot.

## Test Suite Support for Refactor

The test suite is large and appears to cover the domains impacted by this refactor.

Notable large tests (by size, indicative of coverage depth):
- Table validation and rendering tests
- MCP session lifecycle and group security tests
- Web discovery endpoints and render proxy tests

This is a strong alignment with the spec’s “refactor in small steps with tests remaining green” principle.

One caveat:
- `test/test_code_quality.py` still suggests installing ruff with pip in a skip message. That is inconsistent with current repo conventions (UV). It does not break correctness, but it is a “maintenance papercut” that causes confusion.

## Overall Assessment: Structure and Ease of Maintenance

### What is working well
- Clear domain-oriented folder structure under `app/`.
- MCP server refactor is executed in a way that is consistent with the spec’s constraints (thin shim, split modules).
- Explicit behavior-preserving documentation in refactored modules.
- Strong test coverage around the refactor-sensitive areas.

### What is still high-risk / high-cost to maintain
- Web server remains a large multi-responsibility module.
- Management CLIs remain large, mixing parsing + business logic + filesystem/locking.
- Session manager remains a large facade with too many reasons to change.
- Table validator remains a large “validator wall”.
- `tool_schemas.py` is isolated (good) but still large and likely to cause merge conflicts.

### Concrete next refactor steps (still spec-aligned)

If continuing with the spec sequencing:
1) Sessions split next
- Highest leverage: reduces duplication inside MCP tool handlers and makes group/session checks easier to centralize.

2) Web server split
- Purely navigational, but will reduce coupling between auth, images, discovery, render/proxy.

3) Management CLI split
- Extract common path resolution and command functions into `app/management/cli/`.

4) Table validator split
- Move rule groups into small modules; keep `TableData` stable.

5) `tool_schemas.py` internal structure
- Consider splitting into per-domain schema lists, still assembled by `build_tools()` to preserve list_tools output order.

## Open Questions / Clarifications

1) Is the current state “MCP refactor complete” and you want to proceed with the next spec step (sessions split), or do you want to finish the MCP cleanup first (de-dup session/group enforcement helper, tool_schemas structure)?

2) For the web server refactor: do you want the spec’s split to happen inside `app/web_server/` only (no new external imports), or is it acceptable to move some shared HTTP/auth utilities into a shared module (e.g., `app/auth/`)?
