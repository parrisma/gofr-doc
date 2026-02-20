# Spec: Add image_from_url Fragment to news_email Template

Date: 2026-02-18

## Goal

Allow the existing MCP tool `add_image_fragment` (which adds fragment_id `image_from_url`) to work with the `news_email` template by defining that fragment in the template schema and providing a corresponding fragment Jinja template.

This resolves the current error:
- INVALID_FRAGMENT_PARAMETERS: Fragment 'image_from_url' not found in template 'news_email'

## Non-goals

- Do not change MCP tool names, payload shapes, error codes, or routing.
- Do not change `add_image_fragment` behavior (URL validation, embedding behavior, required fields).
- Do not redesign email layout beyond adding a minimal, safe image fragment rendering.
- Do not add new global parameters to the template.

## Current State

- `app/mcp_server/tools/fragments.py` always calls `SessionManager.add_fragment(..., fragment_id="image_from_url", ...)` for `add_image_fragment`.
- `news_email` template schema only declares `news` and `disclaimer` fragments in its `template.yaml`.
- `basic_report` already declares `image_from_url` and provides a working fragment template.

## Proposed Change

1) Template schema change
- Add a new fragment entry to `data/templates/public/news_email/template.yaml`:
  - fragment_id: image_from_url
  - parameters: match the existing `image_from_url` schema used by `basic_report`

2) Template fragment file
- Add `data/templates/public/news_email/fragments/image_from_url.html.jinja2`.
- Rendering behavior:
  - If a title is provided, render it above the image.
  - Render an <img> using embedded_data_uri when present, otherwise image_url.
  - Respect optional width and height attributes when provided.
  - Use minimal inline styling to keep email clients compatible.

## Compatibility and Behavioral Impact

- This is a behavior change at the template capability level (new fragment supported by `news_email`).
- It should not change behavior for other templates.
- It should not change behavior for existing `news_email` sessions that do not use the new fragment.

## Validation and Testing

- Add or extend tests to cover:
  - Creating a `news_email` session and adding an image via `add_image_fragment` succeeds.
  - Rendering includes an <img> tag (and uses embedded_data_uri when present) in HTML output.
- Run the full suite using `./scripts/run_tests.sh`.

## Assumptions (Confirm)

A1. `news_email` should support the same `image_from_url` parameter contract as `basic_report` (no template-specific deviations).
A2. Minimal inline styling in the new fragment is acceptable (to avoid relying on template CSS classes that may not exist).
A3. It is acceptable to add tests to cover the new capability.
