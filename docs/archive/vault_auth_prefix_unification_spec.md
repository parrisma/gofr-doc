# Vault auth path prefix unification spec (gofr-doc)

## Goal
Ensure all gofr services share one canonical Vault auth path prefix: gofr/auth.

This removes a historical per-service derived prefix which causes:
- tokens minted under gofr/auth to fail verification in services configured for a different auth prefix ("Token <jti> not found in token store")
- duplicated/orphaned groups and tokens across two Vault locations

## Background / symptom
We observed gofr-doc MCP running with a non-canonical GOFR_DOC_VAULT_PATH_PREFIX while auth tooling minted tokens into gofr/auth. The JWT signature verified, but store-backed verification failed because the token record did not exist under the service's configured Vault path prefix.

## Scope
In-scope changes are limited to:
- gofr-doc test and tooling defaults
- gofr-common policy definitions vendored in this repo
- gofr-doc start scripts hardening against the wrong prefix value

Out of scope:
- deleting or migrating data in Vault under any deprecated per-service auth prefix
- changing group or token semantics
- changing JWT audience (aud should remain gofr-api)

## Desired canonical settings
- Vault auth path prefix: gofr/auth
- JWT audience: gofr-api

## Inventory: remaining deprecated auth prefix references
Non-archive/non-log references currently found:
- test/conftest.py: server_auth_service fixture default
- lib/gofr-common/src/gofr_common/auth/policies.py: POLICY_DOC_READ auth path permissions

Archive docs and historical logs also contain deprecated prefix references. These do not affect runtime but may confuse readers.

## Proposed changes
1) Tests: gofr-doc integration fixtures
- Update test/conftest.py so server_auth_service uses default gofr/auth when GOFR_DOC_VAULT_PATH_PREFIX is not set.
- Update comments in that section to reflect canonical gofr/auth.

2) Vault policies (gofr-common)
- Update POLICY_DOC_READ to grant read/write/list for secret/data/gofr/auth/* and secret/metadata/gofr/auth/* (canonical shared path).
- Rationale: gofr-doc must operate on shared groups/tokens.

3) Script hardening (optional but recommended)
- Update docker/start-prod.sh (and optionally scripts/run_tests.sh) to prevent accidental override of GOFR_DOC_VAULT_PATH_PREFIX away from gofr/auth from the caller environment.
- Default behavior: if GOFR_DOC_VAULT_PATH_PREFIX is unset -> set to gofr/auth.
- Safety behavior: if GOFR_DOC_VAULT_PATH_PREFIX is set to a non-canonical value -> replace with gofr/auth and emit a warning.

4) Documentation cleanup (optional)
- Either leave archive docs as-is (historical record), or update archive docs to clearly label deprecated prefixes as incorrect.

## Acceptance criteria
- No runtime path uses a non-canonical auth prefix for auth groups/tokens.
- A token minted via auth_manager.sh under gofr/auth verifies successfully in gofr-doc MCP/web without requiring special env overrides.
- Test suite continues to pass using ./scripts/run_tests.sh.

## Assumptions / decisions to confirm
A1. We should change gofr-doc tests and gofr-common policies to gofr/auth and stop supporting non-canonical auth prefixes for any runtime path.
A2. We should harden docker/start-prod.sh to override any non-canonical value, even if the user exported it in their shell.
A3. Archive docs/logs do not need to be rewritten; they can remain as historical context.
