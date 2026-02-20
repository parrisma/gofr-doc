# gofr-plot Migration Plan -- Senior Engineering Review

Reviewer: Senior Systems Engineer
Date: 2025-02-17
Document under review: `docs/gofr-plot-migration-plan.md`

---

## Overall Assessment

The plan is **coherent and well-structured**. Scope is clearly bounded, the phased approach is incremental and independently verifiable, and the technical decisions align with the existing gofr-doc codebase. A few issues need attention before execution.

---

## Validated Assumptions (confirmed against codebase)

1. **Storage kwargs support** -- Confirmed. `gofr_common.storage.FileStorage.save()` accepts `**kwargs` which flow into `BlobMetadata.extra`. The metadata-tagging approach (`artifact_type="plot_image"`, `plot_alias`) will work without any changes to gofr-common.

2. **`image_from_url` fragment + `embedded_data_uri`** -- Confirmed. `_tool_add_image_fragment` already downloads images, builds `data:image/<type>;base64,...` URIs, and stores them as `embedded_data_uri` in fragment parameters. The `add_plot_fragment` tool can reuse this exact pattern.

3. **Group injection in `handle_call_tool`** -- Confirmed. The MCP server injects `arguments["group"]` from the JWT after verification. Plot tool handlers will automatically receive the authoritative group via this mechanism.

4. **Token-optional tools set** -- Confirmed. `TOKEN_OPTIONAL_TOOLS` exists and controls which tools skip authentication. Adding `list_themes` and `list_handlers` to this set is straightforward.

5. **Proxy endpoint** -- Confirmed. `GET /proxy/{proxy_guid}` exists in the web server and delegates to `RenderingEngine.get_proxy_document()`. The plan correctly avoids overloading this endpoint.

6. **CommonStorageAdapter** -- Confirmed. gofr-doc defaults to `CommonStorageAdapter` wrapping `gofr_common.storage.FileStorage`. The plot storage wrapper should wrap the same adapter instance or share the same underlying store.

---

## Issues Found

### Issue 1: auth_token vs token parameter naming (inconsistency)

The plan repeatedly states the tools should accept `auth_token` as the tool parameter name, citing "gofr-dig convention". However, the current gofr-doc `_verify_auth()` extracts `arguments.get("token")` -- not `arguments.get("auth_token")`. The plan claims backward compatibility with `token` but designates `auth_token` as primary.

**Impact**: Either `_verify_auth()` must be updated to check `arguments.get("auth_token")` first (then fall back to `token`), or the plan should be explicit that this is a refactoring step that affects ALL existing tools, not just plot tools.

**Recommendation**: Add a sub-step to Step 4 (or as a separate step) that updates `_verify_auth()` to check `auth_token` first, then `token` for backward compatibility. Document this as a cross-cutting change. Alternatively, if the intent is to NOT change existing tools, then plot tools should use `token` (matching the current convention) and the `auth_token` migration should be a separate effort.

### Issue 2: Step 1 says "pip install -e ." -- violates project rules

The acceptance criterion for Step 1 says "Verify `pip install -e .` works in dev container". The project mandates `uv` only -- never pip.

**Fix**: Change to `uv sync` or `uv add matplotlib numpy` and verify with `uv run python -c "import matplotlib, numpy"`.

### Issue 3: Tool count math

The plan says "register 6 new tools" and then lists 5 ported tools (`render_graph`, `get_image`, `list_images`, `list_themes`, `list_handlers`) plus 1 new tool (`add_plot_fragment`) = 6 total. But it also says "Do not add a second ping; reuse gofr-doc ping" -- so `plot_ping` is explicitly excluded. The count is correct but the prose around it is confusing because it first lists `plot_ping` as a question mark and then says "do not add". The text should just state "5 ported tools + 1 new bridge tool = 6 new tools" without the `plot_ping` discussion.

### Issue 4: Missing Step -- Pydantic validation models

Step 4 mentions "Parse/validate request via Pydantic (GraphParams)" but there is no step to create the Pydantic input models for the new tools (analogous to `CreateDocumentSessionInput`, `AddImageFragmentInput`, etc. in `app/validation/document_models.py`). These models are required for the `handle_call_tool` Pydantic validation error handler to work properly.

**Recommendation**: Add to Step 2 or Step 4: "Create Pydantic input models for `render_graph`, `get_image`, `list_images`, and `add_plot_fragment` in `app/validation/plot_models.py`."

### Issue 5: Storage adapter integration unclear

Step 3 says "Add a thin plot-storage wrapper" but does not specify whether this wrapper:
- (a) Gets its own `CommonStorageAdapter` instance (separate metadata.json, separate blob dir), or
- (b) Shares the same `CommonStorageAdapter` instance used by document storage (same metadata.json, filtering by `artifact_type`)

Option (a) is simpler (no metadata collision risk) but contradicts the plan's own stated preference for "one storage mechanism". Option (b) matches the stated design but requires changes to `CommonStorageAdapter` to pass `**kwargs` through to gofr-common (the current `save_document` signature does NOT pass `**kwargs`).

**Evidence**: `CommonStorageAdapter.save_document(document_data, format, group)` does NOT forward kwargs to `self._storage.save()`. If option (b) is intended, the adapter must be updated.

**Recommendation**: Clarify which option. If (b), add "Update `CommonStorageAdapter.save_document` to accept and forward `**kwargs` to `self._storage.save()`" as a prerequisite sub-step.

### Issue 6: No rollback / feature-flag strategy

The plan adds 6 tools and a new domain package. If something goes wrong post-merge, there is no way to disable plot functionality without reverting the entire change. Consider a feature flag (`GOFR_DOC_PLOT_ENABLED=true/false`) that conditionally registers the plot tools in `handle_list_tools` and `HANDLERS`.

**Recommendation**: Optional but prudent for a change of this scope.

### Issue 7: Headless matplotlib backend not addressed in Step 2

The risk section mentions "ensure matplotlib backend works in container (typically Agg works by default)" but no step actually configures or verifies this. If the container has no display server, matplotlib may default to a backend that fails.

**Recommendation**: Add to Step 2: set `matplotlib.use('Agg')` at import time in the renderer module, and add a unit test that renders a minimal chart.

### Issue 8: Docker image size impact not quantified

matplotlib + numpy add ~100-200 MB to the Docker image. The plan notes this as a risk but assigns no acceptance criterion.

**Recommendation**: Add to Step 1 acceptance: "Docker image size delta is documented and acceptable."

---

## Structural Observations (non-blocking)

- The plan correctly avoids bringing gofr-plot's separate web service into gofr-doc. This is the right call.
- The `add_plot_fragment` bridge tool is well-designed. The two-path approach (GUID vs inline) gives callers flexibility without requiring them to understand storage internals.
- The plan is silent on housekeeper integration. If proxy-mode plot images are stored via CommonStorageAdapter, they should age out under the same TTL rules as document proxy artifacts. Worth confirming this "just works" (it likely does since they share the storage mechanism).
- The plan does not mention updating `HANDLERS` dict and `handle_list_tools` in the same step. Both must be updated atomically. This is implicit but should be explicit.
- Step 5 references "existing 571 tests" -- this number will likely change before execution. Use "existing test suite" instead of a hard count.

---

## Verdict

**All issues have been resolved and applied to the migration plan. The plan is approved for execution.**

Resolutions applied (2025-02-17):

| Issue | Resolution |
|---|---|
| 1. auth_token vs token | Added Step 3b: update `_verify_auth()` to check `auth_token` first, fall back to `token`. Cross-cutting change. |
| 2. pip -> uv | Step 1 now uses `uv add` / `uv sync` / `uv run`. |
| 3. Tool count prose | Step 4 rewritten: "5 ported + 1 new bridge = 6 new tools". No `plot_ping` discussion. |
| 4. Pydantic models | Added to Step 2: create `app/validation/plot_models.py` with input models for all plot tools. |
| 5. Storage option | Option B confirmed. Step 3 now specifies shared `CommonStorageAdapter` instance with prerequisite sub-step to forward `**kwargs`. |
| 6. Feature flag | Not needed -- fail forward or git revert. No change to plan. |
| 7. Matplotlib Agg | Step 2 now requires `matplotlib.use('Agg')` at import time + headless unit test. |
| 8. Docker size | Step 1 acceptance now includes "Docker image size delta is documented and acceptable". |
