# Implementation Plan: Add image_from_url Fragment to news_email

Date: 2026-02-18

This plan executes the approved spec in `docs/news_email_image_from_url_spec.md`.

Rules:
- Use `./scripts/run_tests.sh` for all test runs.
- Keep changes minimal and focused.
- Add tests for the new capability.

## Step 1 - Baseline tests [DONE]

- Run a targeted baseline:
  - `./scripts/run_tests.sh -k "image_fragment or image_rendering or news_email" -v`
- If baseline fails, stop and fix baseline before proceeding.

## Step 2 - Update template schema [DONE]

- Edit `data/templates/public/news_email/template.yaml`.
- Add a new fragment under `fragments:` with fragment_id `image_from_url`.
- Copy the parameter schema contract from `data/templates/public/basic_report/template.yaml`:
  - image_url (required)
  - title, width, height, alt_text, alignment (optional)
  - validated_at, content_type, content_length, require_https, embedded_data_uri (optional, injected)

Verification:
- Run targeted tests from Step 1.

## Step 3 - Add fragment Jinja template [DONE]

- Create `data/templates/public/news_email/fragments/image_from_url.html.jinja2`.
- Implement minimal HTML rendering consistent with existing `image_from_url` behavior:
  - optional title above image
  - <img src> uses embedded_data_uri if present else image_url
  - optional width/height attributes
  - minimal inline style for email client compatibility

Verification:
- Run targeted tests from Step 1.

## Step 4 - Add/extend tests [DONE]

- Add a test that:
  - creates a document session for template_id `news_email`
  - calls `add_image_fragment`
  - expects success (no INVALID_FRAGMENT_PARAMETERS)

- Add a rendering assertion:
  - HTML output contains an <img> tag
  - src equals embedded_data_uri when embedding succeeded (or equals image_url if embedding is not performed in that test environment)

Verification:
- Run targeted tests from Step 1.

## Step 5 - Full acceptance test [DONE]

- Run `./scripts/run_tests.sh`.
- If any failures, fix them before considering work complete.

## Step 6 - Sanity check for discovery [DONE]

- Confirm `get_fragment_details` for template `news_email` and fragment `image_from_url` now returns the schema.
- (This is validated indirectly if MCP discovery tests exist; otherwise validate manually.)

## Completion Criteria

- `add_image_fragment` succeeds for a `news_email` session.
- HTML rendering includes the image.
- Full test suite passes with `./scripts/run_tests.sh`.
