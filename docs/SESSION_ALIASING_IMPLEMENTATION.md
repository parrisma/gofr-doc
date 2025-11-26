# Session Aliasing Implementation Guide

A complete guide for implementing user-friendly session aliases in document generation or session-based servers. This guide covers the 10-phase implementation used in doco that evolved from the problem: "Is it easier for LLMs to remember a name or a GUID?"

## Problem Statement

- **Issue**: LLMs and users struggle to remember long session UUIDs (e.g., `550e8400-e29b-41d4-a716-446655440000`)
- **Solution**: Require friendly, memorable aliases (e.g., `q4-report`, `invoice-march`) as the primary session identifier
- **Benefits**: Self-documenting, memorable, persistent, LLM-friendly

## Core Architecture

### Data Model

- **Aliases**: 3-64 character strings (alphanumeric + hyphens/underscores)
- **Uniqueness**: Per-group (allow reuse across groups in multi-tenant systems)
- **Immutability**: Set at session creation, cannot change
- **Persistence**: Stored alongside session data, survive server restarts
- **Bidirectional mapping**: Both `alias→GUID` and `GUID→alias` lookups

### Validation Regex

```python
^[a-zA-Z0-9_-]{3,64}$
```

**Examples:**
- ✅ Valid: `q4-report`, `invoice_march_2024`, `weekly-summary-v2`
- ❌ Invalid: `x` (too short), `my report` (spaces), `report!!!` (special chars)

## 10-Phase Implementation Plan

### Phase 1: SessionManager Aliasing Core

**Goal**: Implement bidirectional alias mapping and resolution logic

**Changes**:
- Add `_alias_to_guid: Dict[str, Dict[str, str]]` for group-scoped alias→UUID lookups
- Add `_guid_to_alias: Dict[str, str]` for UUID→alias reverse lookups
- Implement `_is_valid_alias(alias: str) -> bool` with regex validation
- Implement `_register_alias(session_id: str, alias: str, group: str)` for registration
- Implement `_unregister_alias(session_id: str)` for cleanup on session deletion
- Implement `resolve_session(identifier: str, group: str) -> str` to handle both alias and UUID
- Implement `get_alias(session_id: str) -> Optional[str]` for reverse lookup

**Tests**: 12 unit tests covering validation, registration, resolution, group isolation

### Phase 2: Required Alias in Session Creation

**Goal**: Make aliases mandatory and update input/output models

**Changes**:
- Update `CreateDocumentSessionInput` model: add required `alias: str` field
- Update `DocumentSession` model: add `alias: Optional[str]` field
- Update `CreateSessionOutput` model: add `alias: Optional[str]` to response
- Update session creation logic: `create_session(alias: str, ...)` parameter
- Call `_register_alias()` during session creation
- Call `_unregister_alias()` during session deletion

**Tests**: 8 tests covering valid/invalid aliases, duplicates, persistence

### Phase 3: Update Session Tools to Accept Aliases

**Goal**: Make all session tools accept either alias or UUID for session identification

**Tools to update** (8 total):
1. `set_global_parameters`
2. `add_fragment`
3. `add_image_fragment`
4. `remove_fragment`
5. `list_session_fragments`
6. `abort_session`
7. `get_session_status`
8. `get_document`

**Implementation pattern**:
```python
async def _tool_set_global_parameters(arguments: Dict[str, Any]) -> ToolResponse:
    payload = SetGlobalParametersInput.model_validate(arguments)
    manager = _ensure_manager()
    
    # NEW: Resolve alias to UUID
    session_id = manager.resolve_session(payload.session_id, payload.group)
    if not session_id:
        return _error("SESSION_NOT_FOUND", "Session not found")
    
    # ... rest of logic uses resolved UUID
```

**Changes to each tool**:
- Add helper function: `_resolve_session_identifier(identifier, group, manager)` in MCP server
- Call resolver before accessing session: `session_id = resolve_session(identifier, group)`
- Update tool schemas to mention alias support in descriptions

**Tests**: Existing tool tests verify alias resolution works

### Phase 4-6: Fragment and Parameter Tools

**Status**: Covered by Phase 3 (already included in tool updates)

### Phase 7: Update Web Endpoints

**Goal**: Make REST API accept aliases in URL paths and request bodies

**Endpoints to update**:
- `POST /render/{session_id}` - accept alias in path parameter
- `POST /session/{session_id}/parameters` - accept alias in path
- `POST /session/{session_id}/fragment` - accept alias in path
- All fragment management endpoints using session_id in path

**Implementation**:
```python
@app.post("/render/{session_id}")
async def render_document(session_id: str, request: RenderRequest):
    # Resolve alias to UUID
    actual_id = await session_manager.resolve_session(session_id, group)
    # ... render using actual_id
```

**Tests**: 52+ web API tests verifying alias works in all endpoints

### Phase 8: Add Alias Information to List Sessions Tool

**Goal**: Enhance session discovery by returning aliases in list output

**Changes**:
- Update `SessionSummary` model: add `alias: Optional[str] = None` field
- Update `list_active_sessions()` method to populate alias: `alias=self.get_alias(session_id)`
- Update `list_active_sessions` tool description to emphasize alias discovery
- New test: verify alias field is present in list output

**Benefit**: LLMs can call `list_active_sessions()` to discover available sessions by memorable name

**Tests**: 1 new test + existing list tests

### Phase 9: Documentation Updates

**Goal**: Update all user-facing documentation to emphasize alias-first approach

**Files to update**:
- `README.md`
  - Update REST API examples to show alias in create_session
  - Show using alias variable instead of UUID in curl examples
  - Emphasize in session tools description that aliases are available everywhere

- `DOCUMENT_GENERATION.md`
  - Add "Quick Start: Session Aliases" section at top
  - Add comprehensive "Session Aliases" concept section
  - Update all workflow examples to use aliases (e.g., `q4-report`)
  - Add `list_active_sessions` tool documentation
  - Update all tool examples: `session_id` → `session_id: "q4-report"`
  - Add tips highlighting alias benefits
  - Update best practices to put aliases first

- `INTEGRATIONS.md`
  - Update n8n workflow examples to use aliases
  - Show alias creation in Step 1
  - Update all subsequent endpoint URLs

**Key messaging**:
- "Aliases work everywhere session_id is accepted"
- "Use memorable names instead of UUIDs"
- "Call list_active_sessions to discover session aliases"
- Examples: `q4-report`, `invoice-march`, `weekly-summary`

### Phase 10: Integration Tests with Aliases

**Goal**: Create end-to-end tests proving complete workflows using only aliases (no GUIDs)

**Test file**: `test/workflow/test_alias_workflow.py`

**Test scenarios**:
1. **Basic workflow**: Create → set params → add fragments → render, using alias in every step
2. **Discovery workflow**: Create multiple sessions → list_active_sessions → use discovered aliases
3. **Iterative workflow**: Create session → render → add more fragments → re-render, all with alias
4. **Multi-format workflow**: Render same session to HTML, PDF, Markdown using alias
5. **Persistence workflow**: Create session → close connection → reconnect → list → find by alias
6. **Error handling**: Try operations with wrong alias → verify error handling

**Test structure**:
```python
@pytest.mark.asyncio
async def test_complete_alias_only_workflow():
    """Demonstrates complete session lifecycle using ONLY aliases, never UUIDs"""
    # 1. Create with alias
    create_document_session(template_id="...", alias="my-report")
    
    # 2. Use alias everywhere
    set_global_parameters(session_id="my-report", ...)
    add_fragment(session_id="my-report", ...)
    
    # 3. Discover by alias
    sessions = list_active_sessions()
    # Find sessions with memorable names
    
    # 4. Render using alias
    pdf = get_document(session_id="my-report", format="pdf")
```

**Key validation**:
- Workflow never uses UUID returned from create_document_session
- All operations refer to session by alias only
- User never needs to copy/paste/remember UUIDs

## Implementation Checklist

- [ ] Phase 1: SessionManager alias core (validation, registration, resolution)
- [ ] Phase 2: Require alias parameter in create_session
- [ ] Phase 3: Update 8 session tools to resolve aliases
- [ ] Phase 4-6: Verify fragment tools work with aliases (via Phase 3)
- [ ] Phase 7: Update web endpoints to accept aliases in paths
- [ ] Phase 8: Add alias field to SessionSummary, update list_sessions
- [ ] Phase 9: Update README, DOCUMENT_GENERATION, INTEGRATIONS docs
- [ ] Phase 10: Create integration tests proving alias-only workflows

## Testing Strategy

**Unit tests** (Phase 1-2):
- Alias validation (valid/invalid formats)
- Alias registration and unregistration
- Alias uniqueness per group
- UUID/alias resolution

**Tool tests** (Phase 3):
- Each tool accepts alias instead of UUID
- Alias resolution returns correct session
- Invalid aliases return SESSION_NOT_FOUND

**Web API tests** (Phase 7):
- Path parameters accept alias
- Request bodies accept alias
- Endpoint responses include alias

**Integration tests** (Phase 10):
- Complete workflows using only aliases
- Session discovery via list_active_sessions
- Multi-step operations with alias persistence
- Cross-format rendering with alias

## Error Handling

When alias is invalid or session not found:
- Return `SESSION_NOT_FOUND` error code (generic, no information leakage in multi-tenant)
- Include helpful message: "Session '{alias}' not found in your group"
- Suggest recovery: "Call list_active_sessions to discover available sessions"

## Security Considerations

**Multi-tenant isolation**:
- Aliases are unique per group, not globally
- Different groups can use same alias
- Prevent information leakage: don't reveal if alias exists in different group

**Access control**:
- Verify `session.group == caller.group` after alias resolution
- Return generic SESSION_NOT_FOUND for cross-group access attempts

## Migration Path

If implementing in existing system:
- Make alias optional initially (Phase 2: `alias: Optional[str] = None`)
- Generate default alias if not provided: `alias = session_id[:8] or uuid4_alias`
- Gradually require alias in new code
- Update documentation to emphasize alias usage
- Eventually make alias mandatory in new major version

## Code Organization

**Core logic**:
- SessionManager: `app/sessions/manager.py`
- Models: `app/validation/models/inputs.py`, `outputs.py`

**Tool integration**:
- MCP server: `app/mcp_server/mcp_server.py`
- Web server: `app/web_server/web_server.py`
- Helper: `_resolve_session_identifier()` function

**Documentation**:
- Concept explanation: `docs/DOCUMENT_GENERATION.md`
- Examples: `README.md`, `docs/INTEGRATIONS.md`
- Implementation guide: `docs/SESSION_ALIASING_IMPLEMENTATION.md` (this file)

## Example Workflow Code

### MCP (Python Client)

```python
# Create session with alias
result = await session.call_tool(
    "create_document_session",
    arguments={"template_id": "basic_report", "alias": "q4-report"}
)
session_id = result["data"]["session_id"]  # UUID, but we won't use it

# Use alias instead
await session.call_tool(
    "set_global_parameters",
    arguments={"session_id": "q4-report", "parameters": {...}}
)

# Discover available sessions
sessions = await session.call_tool("list_active_sessions", arguments={})
# Response includes: [{session_id: "...", alias: "q4-report", ...}, ...]

# Render using alias
pdf = await session.call_tool(
    "get_document",
    arguments={"session_id": "q4-report", "format": "pdf"}
)
```

### REST API (cURL)

```bash
# Create with alias
curl -X POST http://localhost:8010/sessions \
  -H "Content-Type: application/json" \
  -d '{"template_id": "basic_report", "alias": "q4-report"}'

# Use alias in subsequent calls
SESSION="q4-report"

curl -X POST "http://localhost:8010/sessions/$SESSION/parameters" \
  -d '{"title": "Q4 Report", "author": "Data Team"}'

curl -X POST "http://localhost:8010/sessions/$SESSION/render?format=pdf"
```

## Benefits Summary

| Aspect | Without Aliases | With Aliases |
|--------|-----------------|--------------|
| **Memorability** | UUID strings forgettable | Memorable names |
| **Self-documenting** | `550e8400...` unclear | `q4-report` self-explanatory |
| **LLM-friendly** | Hard to remember/reference | Easy for AI to work with |
| **Discovery** | Must know UUID | `list_sessions` finds by name |
| **Debugging** | Logs full of UUIDs | Logs show meaningful names |
| **User experience** | Copy/paste UUIDs | Type memorable name |

## Further Enhancements

- **Alias templates**: Suggest aliases based on template (e.g., `report-{date}`)
- **Alias search**: Full-text search in list_sessions with aliases
- **Alias versioning**: `report-v1`, `report-v2` for iterative sessions
- **Alias metadata**: Tags or descriptions alongside aliases
- **Auto-cleanup**: Suggest removing unused aliases after X days
