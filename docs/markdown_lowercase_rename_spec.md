# Spec: Rename All Markdown Files to Lowercase

## Goal
Standardize all Markdown documentation filenames to lowercase across the entire repository.

## Background / Problem
The repo currently mixes uppercase and lowercase Markdown filenames (e.g., FEATURES.md). This creates inconsistency and can cause friction across tooling, links, and future conventions.

## Scope
In scope:
- Rename every `*.md` file anywhere in the repository (including but not limited to `docs/`, `app/`, `test/`, repo root, and nested folders) so the path is strictly lowercase.
- Preserve existing separators and characters; only change case.
  - Example: `JWT_SECRET_PROVIDER_SPEC.md` -> `jwt_secret_provider_spec.md`
  - Example: `SESSION_ALIASING_IMPLEMENTATION.md` -> `session_aliasing_implementation.md`
- Update references to renamed files (best effort) across:
  - Markdown links in all `.md` files
  - References from README and other docs
  - References from scripts/configs that mention `.md` paths

Out of scope:
- Changing document content beyond link/filename references.
- Normalizing naming conventions beyond case (no underscore/hyphen changes).
- Adding redirects or compatibility layers for external links.

## Non-Goals
- Not changing folder names.
- Not changing non-Markdown files.

## Constraints
- Git history should be preserved via rename operations (not delete/add).
- The change will be delivered as a single commit containing both renames and reference updates.
- The project must remain in a passing state: run the full test suite before and after.

## Risks
- External links (outside this repo) that point to existing uppercase paths will break.
- Case-only renames can be tricky on case-insensitive filesystems; while this workspace is Linux, contributors on other platforms might run into local tooling edge cases.
- Potential name collisions if two Markdown files differ only by case once lowercased.

## Assumptions (must be confirmed)
- The repository does not intentionally rely on case distinctions between two `.md` files in the same directory.
- Updating references "best effort" is acceptable; the acceptance criteria is: no obvious broken internal links remain after search-based updates.

## Acceptance Criteria
- All `*.md` paths in the repo are lowercase.
- All internal references in the repo that point to renamed Markdown files are updated to match the new paths.
- Full test suite passes.

## Rollback Plan
- Revert the single commit.
