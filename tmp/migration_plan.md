# gofr-doc Auth Migration Plan

**Date:** 2026-02-15  
**Baseline:** commit `3351db9` (clean reset)  
**Reference:** gofr-dig (read-only mount at `../gofr-dig`)  
**gofr-common target:** `f1572c4` (matches gofr-dig)

## Principle

Follow gofr-dig's patterns exactly. No dual-mode, no in-memory stores, no
`auth_test_helpers.py`. All auth is Vault-backed. Each test gets a unique
Vault path prefix for isolation.

---

## Phase 1: Submodule Update

- [x] Update `lib/gofr-common` from `a6fccdf` → `f1572c4`
- [x] Switch remote to HTTPS (PAT-based auth)
- [x] Stage with `git add -f lib/gofr-common`

---

## Phase 2: Server Entry Points

Migrate `app/main_mcp.py` and `app/main_web.py` to match gofr-dig's pattern.

### Changes required

**app/main_mcp.py:**
- Remove `--token-store` argument
- Import `create_stores_from_env, GroupRegistry` from `gofr_common.auth`
- Import `resolve_auth_config` from `gofr_common.auth.config` (not app wrapper)
- Change `resolve_auth_config` call: returns `(jwt_secret, require_auth)` not `(jwt_secret, token_store_path)`
- Change `AuthService(...)` to: create stores via `create_stores_from_env("GOFR_DOC")`, then `GroupRegistry(store=group_store)`, then `AuthService(token_store=, group_registry=, secret_key=, env_prefix="GOFR_DOC")`

**app/main_web.py:**
- Same changes as main_mcp.py

**Reference:** `../gofr-dig/app/main_mcp.py` (already read, pattern confirmed)

---

## Phase 3: Auth Config Wrapper

**app/startup/auth_config.py:**
- Simplify to match new `resolve_auth_config` signature
- Returns `Tuple[Optional[str], bool]` (jwt_secret, require_auth)
- Remove all `token_store_path` / `token_store_arg` parameters
- Remove `get_default_token_store_path` import
- Keep as thin wrapper with `env_prefix="GOFR_DOC"` defaults

**OR** delete it entirely and import directly from `gofr_common.auth.config`
like gofr-dig does. Decision: **delete the wrapper** — gofr-dig has no
`app/startup/auth_config.py` at all.

---

## Phase 4: Auth Module Init

**app/auth/__init__.py:**
- Update re-exports to match latest gofr-common `__init__.py`
- Add: `GroupRegistry`, `Group`, `TokenRecord`, `create_stores_from_env`,
  `VaultConfig`, `VaultClient`, `VaultTokenStore`, `VaultGroupStore`
- Remove any references to old API (`token_store_path`, etc.)

---

## Phase 5: Test Fixtures (conftest.py)

Rewrite `test/conftest.py` following gofr-dig's conftest exactly.

### Key changes
- Remove `TEST_TOKEN_STORE_PATH` and all file-based token store logic
- Add Vault imports: `VaultClient`, `VaultConfig`, `VaultTokenStore`, `VaultGroupStore`
- Add `_build_vault_client()` — reads `GOFR_DOC_VAULT_URL` + `GOFR_DOC_VAULT_TOKEN`
- Add `_create_test_auth_service(vault_client, path_prefix)` — creates stores + GroupRegistry + AuthService with unique path
- `auth_service` fixture: function-scoped, creates fresh VaultClient + unique `gofr/tests/{uuid4()}` path
- `test_auth_service` fixture: session-scoped, same pattern
- `test_jwt_token`: use `create_token(groups=[TEST_GROUP], ...)` (plural)
- `mcp_headers`: use `create_token(groups=["test_group"], ...)`
- `configure_test_auth_environment`: set `GOFR_DOC_AUTH_BACKEND=vault`, `GOFR_DOC_VAULT_URL`, `GOFR_DOC_VAULT_TOKEN`
- Remove `temp_token_store` fixture (no longer needed)
- `ServerManager` init: remove `token_store_path` param

---

## Phase 6: Test File Fixes

### API changes affecting all test files
| Old API | New API |
|---------|---------|
| `AuthService(secret_key=x, token_store_path=y)` | Use `auth_service` fixture (Vault-backed) |
| `create_token(group="x", ...)` | `create_token(groups=["x"], ...)` |
| `token_info.group` | `token_info.groups` |
| `GOFR_DOC_TOKEN_STORE` env var | `GOFR_DOC_AUTH_BACKEND=vault` + Vault env vars |

### Files needing changes (from grep)
- `test/conftest.py` — Phase 5 above
- `test/test_server_manager.py` — remove `token_store_path`
- `test/auth/test_auth_config.py` — rewrite for new `resolve_auth_config` signature
- `test/auth/test_authentication.py` — use fixtures instead of direct `AuthService()`
- `test/web/test_proxy_auth_security.py` — use fixture, `groups=` plural
- `test/web/test_render_proxy.py` — use fixture instead of direct `AuthService()`
- `test/web/test_discovery_endpoints.py` — use fixture
- `test/web/test_ping_web.py` — use fixture
- `test/web/manual_test_web_server.py` — update (non-critical, manual test)

---

## Phase 7: Test Infrastructure (run_tests.sh)

Update `scripts/run_tests.sh` to start an ephemeral Vault for tests.

### Pattern from gofr-dig's run_tests.sh
- `start_vault_test_container()` — runs `hashicorp/vault:latest` in dev mode on `gofr-test-net` with known token `gofr-dev-root-token`
- Port from `GOFR_VAULT_PORT_TEST` in `gofr_ports.env` (8301)
- Exports `GOFR_DOC_VAULT_URL` and `GOFR_DOC_VAULT_TOKEN`
- Exports `GOFR_DOC_AUTH_BACKEND=vault`
- `trap 'stop_vault_test_container' EXIT` for cleanup
- Code quality gate runs first (fast fail before starting services)

### What NOT to do
- No nohup server processes — servers are started via docker-compose if needed
- No dual-mode addressing — pick docker or localhost based on where tests run

---

## Phase 8: Validate

1. Run full test suite with ephemeral Vault
2. Target: 0 skips, 0 failures
3. Commit all changes

---

## Execution Order

1. Phase 2 + 3 + 4 together (server + auth config, no test deps)
2. Phase 5 (conftest — blocks all test work)
3. Phase 6 (test files — can be parallelized)
4. Phase 7 (run_tests.sh — needed to actually run tests)
5. Phase 8 (validate)

---

## Files to create (new)
None expected. All changes are to existing files.

## Files to delete
- `app/startup/auth_config.py` (replaced by direct import)
- Possibly `test/auth/test_auth_config.py` (tests the deleted wrapper)
