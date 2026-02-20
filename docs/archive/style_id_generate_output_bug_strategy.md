# Issue Strategy: Style ID not applied on Generate Output

## Observed Symptom
- In GOFR-DOC "Render & Proxy" flow, changing `style_id` does not change the rendered output when "Generate output" is pressed.
- Expected: pressing "Generate output" should render using the currently selected `style_id`.

## Confirmed Context
- Entry point: Open WebUI via MCPO (OpenAPI proxy) calling gofr-doc MCP `get_document`.
- Proxy behavior: a new `proxy_guid` is returned each time "Generate output" is pressed.

## Non-negotiables
- Fix root cause; do not introduce behavior changes beyond making `style_id` apply correctly.
- No secrets in logs (JWTs must not be printed).
- Keep existing API/tool response shapes stable.

## Scope Assumptions (MUST confirm)
1. The bug is in gofr-doc rendering/template application (not the Open WebUI proxy layer).
2. The "Generate output" action ultimately calls gofr-doc MCP `get_document`.
3. Proxy mode is enabled in this flow (it is called "Render & Proxy").

## Key Hypotheses
H1. The UI state updates `style_id`, but the request payload sent on "Generate output" does not include the new `style_id`.
- Common causes: stale closure, state not wired, form value not bound, request built from initial values.

H2. The server receives `style_id`, but overrides/ignores it.
- Common causes: server-side default style applied unconditionally, or `style_id` parameter name mismatch.

H3. Proxy caching/reuse returns prior render.
- Common causes:
  - "Generate output" reuses an existing `proxy_guid` rather than generating a new one.
  - The proxy storage key does not include `style_id` so it returns the prior render.

H4. Render pipeline caches compiled templates/CSS in a way that does not vary by `style_id`.
- Less likely given tests, but possible if the web flow uses a separate cache.

## Findings
- Root cause: the `basic_report` document template did not include `{{ css }}` anywhere, so even though the renderer loads the selected style CSS, it was never injected into the output.
- Evidence: `news_email` templates include `{{ css }}` (and style changes apply), while `basic_report` had only hard-coded CSS.

## Fix Implemented
- Updated `data/templates/public/basic_report/document.html.jinja2` to inject `{{ css }}` into the `<style>` block so `style_id` changes affect output on re-render/proxy.

## Validation Plan (no code changes yet)
### V1. Identify the exact call path used by "Generate output"
- Locate UI/endpoint implementing "Render & Proxy".
- Confirm whether it calls:
  - MCP tool `get_document` with `proxy=true`, OR
  - Web REST endpoint that wraps the same renderer.

### V2. Confirm whether the server receives the requested `style_id`
- Add/verify structured logs (no token logging) at the render entrypoint:
  - `session_id`, `style_id`, `format`, `proxy`, `group`.
- Compare:
  - style selected in UI
  - style_id received on the server

### V3. Confirm proxy behavior
- Determine if "Generate output" should:
  - Always generate a new `proxy_guid`, or
  - Reuse a prior `proxy_guid`.
- If it should generate a new one:
  - Verify the handler calls render each time (not returning cached proxy result).
- If it should reuse:
  - Verify the cache key includes `style_id` and `format`.

### V4. Add a regression test (once root cause is proven)
- Add a test that:
  - Creates a session
  - Renders with style A (proxy)
  - Renders again with style B (proxy)
  - Asserts outputs differ (or at minimum proxy GUIDs differ and metadata reflects style B)

## Concrete Diagnostics (next)
- Search for "Generate output" / "render and proxy" UI handler.
- Trace the payload construction and verify `style_id` wiring.
- Trace server handler and proxy storage retrieval logic.

## Verification
- Test run: `./scripts/run_tests.sh -k "proxy" -v`.
- Test run: `./scripts/run_tests.sh`.
- Result: all tests passed.

## Open Questions for User
1. Where do you see this (Web UI page name, or CLI, or MCP client)?
2. Are you rendering with `proxy=true` or direct render?
3. Does the returned `proxy_guid` change when you change style and press "Generate output"?
4. Which output format are you using (html/pdf/md)?
