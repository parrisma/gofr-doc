# JWT Secret Provider -- Implementation Plan

Reference: docs/jwt_secret_provider_spec.md (all assumptions confirmed)

## Baseline

Run full test suite before starting:

    ./scripts/run_tests.sh

Record pass/fail count for comparison at the end.

---

## Steps

### Step 1 -- Create JwtSecretProvider class

File: `lib/gofr-common/src/gofr_common/auth/jwt_secret_provider.py`

- Implement `JwtSecretProvider` with:
  - `__init__(self, vault_client, vault_path, cache_ttl_seconds, logger)`
  - `get() -> str` -- returns cached secret or reads from Vault
  - `fingerprint` property -- sha256 of current cached secret
  - `invalidate()` -- clears cache, next `get()` re-reads
- `threading.Lock` protects `_cached_secret` and `_cache_expires_at`
- On cache refresh where fingerprint changes, log at WARNING with old/new
- On Vault read failure, raise (do not swallow)

### Step 2 -- Export from auth package

File: `lib/gofr-common/src/gofr_common/auth/__init__.py`

- Import and add `JwtSecretProvider` to the module and `__all__`

### Step 3 -- Unit tests for JwtSecretProvider

File: `test/auth/test_jwt_secret_provider.py`

- Test: first `get()` reads from Vault
- Test: second `get()` within TTL returns cached (no Vault call)
- Test: `get()` after TTL expires re-reads from Vault
- Test: fingerprint changes logged at WARNING
- Test: `invalidate()` forces re-read
- Test: Vault read failure raises
- Test: thread safety (concurrent `get()` calls)
- Use mock VaultClient (no real Vault needed for unit tests)

### Step 4 -- Replace `secret_key` with `secret_provider` in TokenService

File: `lib/gofr-common/src/gofr_common/auth/token_service.py`

- Replace `secret_key: Optional[str]` parameter with
  `secret_provider: JwtSecretProvider`
- Remove env-var fallback logic and auto-generated secret logic
- Replace all `self._secret_key` reads with `self._secret_provider.get()`
- Update `secret_key` property to call `self._secret_provider.get()`
- Update `secret_fingerprint` property to delegate to provider

### Step 5 -- Replace `secret_key` with `secret_provider` in AuthService

File: `lib/gofr-common/src/gofr_common/auth/service.py`

- Replace `secret_key: Optional[str]` parameter with
  `secret_provider: JwtSecretProvider`
- Pass provider through to `TokenService`
- Update `_secret_fingerprint()` to delegate to provider
- Update docstring examples

### Step 6 -- Update resolve_auth_config

File: `lib/gofr-common/src/gofr_common/auth/config.py`

- Change `resolve_auth_config()` return type from
  `Tuple[Optional[str], bool]` to `Tuple[Optional[JwtSecretProvider], bool]`
- When auth is required: build VaultClient from AppRole creds at
  `/run/secrets/vault_creds` (or env vars for Vault URL/creds),
  construct `JwtSecretProvider`, return it
- Remove `jwt_secret_arg` parameter
- Remove env-var fallback (`GOFR_JWT_SECRET`)
- Remove auto-generated secret logic
- Remove `_fingerprint_secret()` helper (provider handles this)
- Remove `resolve_jwt_secret_for_cli()` entirely

### Step 7 -- Update app/startup/auth_config.py

File: `app/startup/auth_config.py`

- Remove re-export of `resolve_jwt_secret_for_cli`
- Update `__all__` to only export `resolve_auth_config`

### Step 8 -- Update main_mcp.py

File: `app/main_mcp.py`

- Remove `--jwt-secret` CLI argument
- Update `resolve_auth_config()` call: remove `jwt_secret_arg`
- Change variable name from `jwt_secret` to `secret_provider`
- Pass `secret_provider` to `AuthService` constructor instead of
  `secret_key`

### Step 9 -- Update main_web.py

File: `app/main_web.py`

- Same changes as Step 8 for the web server entry point

### Step 10 -- Update token_manager.py

File: `app/management/token_manager.py`

- Remove `--secret` CLI argument
- Remove `GOFR_JWT_SECRET` env var references
- Build `VaultClient` from AppRole creds (env vars already set by
  `auth_manager.sh`)
- Construct `JwtSecretProvider` directly
- Pass to `AuthService` as `secret_provider`
- Remove import of `resolve_jwt_secret_for_cli`

### Step 11 -- Update entrypoint-prod.sh

File: `docker/entrypoint-prod.sh`

- Remove lines 55-84 (JWT-reading section)
- Remove `GOFR_JWT_SECRET` from header comments
- Keep AppRole credential copying (still needed for the provider)

### Step 12 -- Update compose.dev.yml

File: `docker/compose.dev.yml`

- Remove `GOFR_JWT_SECRET` env var from all service definitions
- Remove `--jwt-secret` from any command strings

### Step 13 -- Update auth_manager.sh

File: `lib/gofr-common/scripts/auth_manager.sh`

- Remove the JWT-reading section (vault_kv_get, JWT_SECRET export)
- Remove `GOFR_JWT_SECRET` from the env export
- Keep AppRole login (still needed -- exports `GOFR_VAULT_TOKEN`,
  `GOFR_VAULT_ROLE_ID`, `GOFR_VAULT_SECRET_ID` for auth_manager.py)

### Step 14 -- Update auth_manager.py

File: `lib/gofr-common/scripts/auth_manager.py`

- Construct `VaultClient` from env vars (`GOFR_VAULT_URL`,
  `GOFR_VAULT_ROLE_ID`, `GOFR_VAULT_SECRET_ID`)
- Construct `JwtSecretProvider` with that client
- Pass to `AuthService` as `secret_provider`
- Remove `GOFR_JWT_SECRET` env var reads

### Step 15 -- Update config_docs.py

File: `app/config_docs.py`

- Remove all references to `GOFR_JWT_SECRET` in config documentation
  strings and validation logic
- Update config examples to remove JWT env var mentions

### Step 16 -- Update existing auth tests

Files: `test/auth/`, `test/mcp/`, `test/web/`

- Update any tests that pass `secret_key` to AuthService/TokenService
  to instead pass a `JwtSecretProvider` (using mock VaultClient)
- Update any tests that set `GOFR_JWT_SECRET` env var to use the
  provider pattern instead
- Create a test helper: `make_test_secret_provider(secret="test-key")`
  that returns a provider backed by a mock VaultClient

### Step 17 -- Run full test suite

    ./scripts/run_tests.sh

- All tests must pass
- Compare pass count with baseline from before Step 1

---

## Not changed (out of scope)

- `auth_env.sh` -- shell-only, not used by Python services
- Vault secret rotation automation
- Token re-issuance on rotation
