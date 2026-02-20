# Vault auth path prefix unification implementation plan

Goal: eliminate runtime/test/policy usage of non-canonical auth prefixes and standardize on gofr/auth.

Rules:
- No Vault data migration/deletion.
- Override/warn if GOFR_DOC_VAULT_PATH_PREFIX is set to a non-canonical value.
- Leave docs/archive and logs unchanged.

## Step 0 - Baseline
- Run ./scripts/run_tests.sh and record pass/fail.

Status: DONE (709 passed)

## Step 1 - Update gofr-doc integration test fixtures
- Change test/conftest.py server_auth_service default to gofr/auth.
- Update nearby comments to reflect canonical gofr/auth.
- Run targeted tests that use server_auth_service (test/mcp/* and test/web/* via ./scripts/run_tests.sh -k or full if cheap).

Status: DONE

## Step 2 - Update gofr-common policy definitions for doc
- Update lib/gofr-common/src/gofr_common/auth/policies.py POLICY_DOC_READ:
  - Ensure auth path permissions are for secret/data/gofr/auth/* and secret/metadata/gofr/auth/*
- Confirm no other non-canonical prefix references remain in non-archive/non-log code.

Status: DONE

## Step 3 - Harden prod startup against wrong env override
- Update docker/start-prod.sh:
  - If GOFR_DOC_VAULT_PATH_PREFIX is unset, set to gofr/auth.
  - If it is set to a non-canonical value, replace with gofr/auth and print a warning.
- Optional: apply the same hardening to scripts/run_tests.sh (test stack) if it reads GOFR_DOC_VAULT_PATH_PREFIX from environment.

Status: DONE

## Step 4 - Verification
- Grep repo for deprecated per-service auth prefixes and confirm remaining hits are only in docs/archive and logs.
- Run ./scripts/run_tests.sh (full) as acceptance.

Status: NOT STARTED

## Step 5 - Wrap-up
- Summarize the changes (files touched) and provide the new canonical env behavior.

Status: NOT STARTED
