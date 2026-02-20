# Sessions Split - Implementation Plan (Behavior-Preserving)

Date: 2026-02-18

This plan implements “Proposed Refactor 4: Split app/sessions/manager.py” from `docs/large_file_refactor_spec.md`.

Constraints (from spec):
- Refactor only: no runtime behavior changes.
- Preserve public APIs and entrypoints.
- Preserve error codes/messages/recovery strategies and logging semantics.
- Each step lands independently with tests green.

## Scope

In scope:
- Split responsibilities currently embedded in `app/sessions/manager.py` into collaborator modules/classes.
- Keep `SessionManager` as the public facade with the same method signatures and semantics.
- Keep existing imports stable where practical; otherwise use internal compatibility re-exports.

Out of scope (unless explicitly approved):
- Changing storage formats, session IDs/aliases formats, or validation logic.
- Changing MCP tool names or request/response payloads.
- Broad re-architecture of registries/rendering.

## Primary Deliverable

Refactor `SessionManager` internals into:
- `app/sessions/aliases.py` -> AliasRegistry
- `app/sessions/lifecycle.py` -> SessionLifecycle
- `app/sessions/mutations.py` -> SessionMutator
- `app/sessions/validation.py` -> SessionReadinessValidator

`SessionManager` composes these collaborators and remains the stable facade.

## Key Decision Needed (Confirm)

D1. Include MCP handler de-dup in the same change set?
- Option A (recommended for lowest risk): Only split sessions internals; do not change MCP tool handlers yet.
- Option B (higher leverage, slightly higher risk): After the sessions split, also introduce one behavior-preserving helper used by MCP tool handlers to centralize “resolve alias -> load session -> verify group -> return SESSION_NOT_FOUND” logic.

This plan is written so Steps 1-8 implement Option A. Steps 9-11 implement Option B and should be treated as optional pending confirmation.

## Baseline / Acceptance Testing

Required test runner:
- Use `./scripts/run_tests.sh` only.

Baseline (before changes):
- Run targeted tests that cover sessions and group security.
- If baseline is already failing, stop and fix baseline first.

Acceptance (after each step / at end):
- Re-run the same targeted tests.
- At the end, run the full suite with `./scripts/run_tests.sh`.

## Step-by-Step Plan

Step 1 - Baseline test run and capture current behavior
- Run `./scripts/run_tests.sh -k "session|alias|group_security|fragment" -v`.
- Record failures (if any) and stop if baseline is red.
- Outcome: known-good starting point.

Step 2 - Map responsibilities inside SessionManager
- Identify and list current responsibilities in `app/sessions/manager.py`:
  - alias validation/registration/unregistration
  - alias persistence load
  - create/get/abort session
  - set globals, add/remove fragments, list fragments
  - readiness validation
  - parameter validation
- Outcome: explicit boundaries for extraction and a checklist of methods to preserve.

Step 3 - Add collaborator module skeletons (no behavior change)
- Create:
  - `app/sessions/aliases.py`
  - `app/sessions/lifecycle.py`
  - `app/sessions/mutations.py`
  - `app/sessions/validation.py`
- Each module should:
  - Have a clear module docstring describing its responsibility.
  - Define a single class with constructor arguments matching what it needs (SessionStore, TemplateRegistry, Logger, etc.).
- Do not modify `SessionManager` yet.
- Verification: targeted tests still pass.

Step 4 - Extract alias responsibilities
- Move alias-specific logic into AliasRegistry:
  - loading aliases from storage
  - validating alias format
  - resolving alias to session GUID within a group
  - registering/unregistering aliases
- Keep exact semantics:
  - same validation rules
  - same lookup precedence
  - same behavior for collisions and invalid aliases
- Update `SessionManager` to delegate to AliasRegistry but keep the same public methods.
- Verification: run targeted tests.

Step 5 - Extract session lifecycle responsibilities
- Move create/get/abort into SessionLifecycle.
- Keep exact semantics:
  - session creation side effects
  - alias assignment behavior
  - error handling and return payloads
- Update `SessionManager` to call SessionLifecycle.
- Verification: run targeted tests.

Step 6 - Extract mutation responsibilities
- Move set_global_parameters, add_fragment, remove_fragment, list_session_fragments into SessionMutator.
- Keep exact semantics:
  - ordering rules (position handling)
  - fragment validation triggers
  - session persistence behavior
- Update `SessionManager` to call SessionMutator.
- Verification: run targeted tests.

Step 7 - Extract readiness/parameter validation responsibilities
- Move validate_session_for_render and validate_parameters into SessionReadinessValidator.
- Keep exact semantics:
  - readiness criteria
  - returned booleans/messages
  - error messages and codes (if any are raised)
- Update `SessionManager` to call SessionReadinessValidator.
- Verification: run targeted tests.

Step 8 - Cleanup and import hygiene (still behavior-preserving)
- Ensure `app/sessions/__init__.py` continues to export the same public symbols used elsewhere.
- Remove now-dead private helpers from `SessionManager` if they have been fully migrated.
- Ensure no circular imports:
  - collaborators should depend on lower-level domain models/stores, not on `SessionManager`.
- Verification:
  - run targeted tests
  - run full suite with `./scripts/run_tests.sh`.

Optional Step 9 (requires D1 Option B) - Add a session+group enforcement helper for MCP tools
- Introduce a single helper (location to decide; likely `app/mcp_server/tools/common.py` or `app/sessions/validation.py`) that:
  - resolves session identifier (alias or GUID)
  - loads the session
  - enforces `session.group == caller_group`
  - returns a generic not-found result for cross-group access
- Acceptance criterion: error code/message/recovery remains identical to current behavior in every tool.

Optional Step 10 (requires D1 Option B) - Update MCP tool handlers to use the helper
- Replace repeated patterns in:
  - `app/mcp_server/tools/fragments.py`
  - `app/mcp_server/tools/rendering.py`
  - `app/mcp_server/tools/sessions.py`
  - `app/mcp_server/tools/plot.py`
- Keep per-tool logging and success payloads unchanged.
- Verification: run MCP-focused tests and full suite.

Optional Step 11 (requires D1 Option B) - Regression validation for security semantics
- Ensure cross-group access attempts still return the same generic SESSION_NOT_FOUND shape.
- Ensure alias resolution behaves identically for valid/invalid aliases and GUIDs.
- Verification: run the group security test set.

## Risks and Mitigations

Risk 1: Subtle behavior drift due to moving code
- Mitigation: extract in small steps, keep method signatures the same, keep return models identical, run targeted tests after each step.

Risk 2: Circular imports after splitting
- Mitigation: collaborators should only depend on stores/models/registries, not on the facade.

Risk 3: Hidden coupling via private methods
- Mitigation: move private helpers together with the responsibility they serve; avoid leaving half-migrated helpers.

## Completion Criteria

- `SessionManager` remains the public facade and external callers continue to work.
- No behavioral changes as verified by:
  - targeted tests passing during the refactor
  - full suite passing at the end using `./scripts/run_tests.sh`.
- New modules are cohesive and have clear reasons to change.
