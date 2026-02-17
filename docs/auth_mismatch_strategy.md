# Auth Mismatch Strategy

## Observed Symptom

Tokens created by `auth_manager.sh` fail validation in gofr-doc prod services with:
1. "Signature verification failed" (now resolved by rebuilding prod image)
2. "Token audience mismatch"
3. "Group 'apac-sales' does not exist" (when minting inside the container)

## Root Cause

Two independently-acting violations of the shared-auth ground truths:

### Mismatch 1 -- Vault Path Prefix

| Component            | Path prefix      | Where set |
|----------------------|------------------|-----------|
| auth_manager.sh/py   | `gofr/auth`      | Default in auth_manager.py line 176 |
| gofr-doc MCP (prod)  | `gofr/doc/auth`  | compose.prod.yml env default |
| gofr-doc WEB (prod)  | `gofr/doc/auth`  | compose.prod.yml env default |
| gofr-doc DEV         | `gofr/doc/auth`  | run-dev.sh env var |
| gofr-doc TEST        | `gofr/doc/auth`  | compose.dev.yml env var |

Effect: auth_manager creates groups and tokens under `secret/gofr/auth/...`
but gofr-doc services look under `secret/gofr/doc/auth/...` -- completely
separate namespaces. Groups and tokens are invisible to each other.

Ground truth violated: #1 (one set of groups) and #2 (one set of tokens).

### Mismatch 2 -- JWT Audience Claim

| Component            | env_prefix   | Derived audience   |
|----------------------|--------------|--------------------|
| auth_manager.py      | `GOFR`       | `gofr-api`         |
| gofr-doc services    | `GOFR_DOC`   | `gofr_doc-api`     |

The audience is derived as `{env_prefix.lower()}-api`. auth_manager defaults
to env_prefix="GOFR" (line 206 -- no env_prefix passed to AuthService).
gofr-doc services pass `env_prefix="GOFR_DOC"` (main_web.py:84, main_mcp.py:93).

Effect: tokens minted by auth_manager carry `"aud": "gofr-api"` but the
service's verify_token() expects `"aud": "gofr_doc-api"` -> "Token audience
mismatch".

Ground truth violated: #2 (tokens must work across all services).

## Fix Plan

Per ground truths: all services share ONE path prefix and ONE audience.

The canonical shared defaults are `gofr/auth` (path) and `gofr-api` (audience).

### Changes Required

1. **compose.prod.yml** -- change GOFR_DOC_VAULT_PATH_PREFIX default from
   `gofr/doc/auth` to `gofr/auth` (two occurrences: mcp, web).

2. **compose.dev.yml** -- same change for the test stack (mcp, web services).

3. **docker/run-dev.sh** -- change GOFR_DOC_VAULT_PATH_PREFIX from
   `gofr/doc/auth` to `gofr/auth`.

4. **app/main_web.py** and **app/main_mcp.py** -- either:
   (a) remove `env_prefix="GOFR_DOC"` from AuthService() so it defaults to
       "GOFR" (audience = "gofr-api"), OR
   (b) pass `audience="gofr-api"` explicitly.
   Option (b) is safer -- it pins the shared audience while letting the
   env_prefix continue to drive other environment variable lookups correctly
   (GOFR_DOC_VAULT_URL, etc.).

5. **scripts/gofr-doc.env** -- if it sets GOFR_DOC_VAULT_PATH_PREFIX, change
   it to `gofr/auth`.

No changes needed in gofr-common (auth_manager.py or lib code). The defaults
there already match the ground truths.

## Assumptions (to validate with user)

- The canonical shared path prefix is `gofr/auth` (matches auth_manager default).
Correct
- The canonical shared audience is `gofr-api` (matches auth_manager default).
Correct
- env_prefix="GOFR_DOC" is still needed for env var lookups (GOFR_DOC_VAULT_URL,
  GOFR_DOC_AUTH_BACKEND, etc.) -- only the audience derivation is wrong.
Correct
- After fixing the path prefix, the existing groups/tokens under `gofr/auth`
  (created by auth_manager) will become visible to gofr-doc services.
As was teh plan all along
- The groups under `gofr/doc/auth` are orphaned duplicates and can be ignored.
Must be DELETED
