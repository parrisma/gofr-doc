# Implementation Plan: Rename All Markdown Files to Lowercase

## Preconditions
- Working tree clean.
- Confirm current branch and remote are in sync.

## Step 0: Baseline
- Run the full test suite to establish a green baseline.

## Step 1: Inventory
- Enumerate all `*.md` files in the repository.
- Compute the target lowercase path for each file.
- Detect collisions where two files would map to the same lowercase path.
  - If collisions exist, stop and resolve with the user before proceeding.

## Step 2: Perform Renames
- Rename each Markdown file to its lowercase target path using git-aware rename operations.
- For any case-only rename that might be problematic on some environments, use a safe two-step rename strategy (temporary name then final name) while keeping git history.

## Step 3: Update References (Best Effort)
- Search the repository for references to the old Markdown paths.
- Update Markdown links and any other textual references to match the new lowercase paths.
- Re-scan for remaining references to old paths.

## Step 4: Verification
- Run the full test suite.
- Spot-check that key docs (README, tools reference, major docs under `docs/`) have no obviously broken internal links.

## Step 5: Commit
- Create a single commit containing:
  - All Markdown file renames
  - All reference updates

## Step 6: Push
- Push the commit to origin.

## Exit Criteria
- Tests pass.
- No remaining references to old-case `.md` paths found by repo-wide search.
