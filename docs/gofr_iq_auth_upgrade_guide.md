# GOFR-IQ auth upgrade guide (align to gofr-doc)

Date: 2026-02-18

## Goal

Upgrade gofr-iq so its authentication and authorization matches the gofr-doc pattern:

- One shared auth architecture across GOFR services.
- Vault is the single source of truth for:
  - JWT signing secret
  - group registry
  - token registry
- Services authenticate to Vault using AppRole credentials mounted at `/run/secrets/vault_creds` (VaultIdentity), with auto-renewal.
- JWT validation uses a fixed audience: `gofr-api`.
- Vault auth path prefix is unified to: `gofr/auth`.
- Services do not require (or accept) per-service JWT secrets like `GOFR_IQ_JWT_SECRET`.

Reference implementation:

- The target model for this upgrade is gofr-doc in this devroot at: `/home/gofr/devroot/gofr-doc`.
- If anything in gofr-iq is unclear (env vars, bootstrap flow, AppRole wiring, Vault paths), reference gofr-doc as the canonical target state.

## What gofr-iq does today (observed)

- gofr-iq expects `GOFR_IQ_JWT_SECRET` (or `GOFR_JWT_SECRET`) and fails startup if it is missing when auth is enabled.
- gofr-iq also performs a startup check that `GOFR_IQ_JWT_SECRET` matches Vault KV at `secret/gofr/config/jwt-signing-secret`.
- gofr-iq wires `AuthService(..., secret_key=...)` via `app/auth/factory.py` ("secret_key" model).
- gofr-iq uses a mixed env-prefix scheme:
  - Vault backend env vars are `GOFR_*` (for example `GOFR_AUTH_BACKEND`, `GOFR_VAULT_URL`, `GOFR_VAULT_PATH_PREFIX`).
  - Server-specific config is `GOFR_IQ_*`.
- gofr-iq is pinned to an older gofr-common commit that predates:
  - `JwtSecretProvider`
  - stricter "vault-only" backend stance
  - newer AppRole provisioning helpers and scripts used by gofr-doc

## Target state (what gofr-doc does)

- gofr-doc constructs `VaultClient` using `create_vault_client_from_env(prefix, ...)`.
  - That path prefers VaultIdentity (AppRole creds at `/run/secrets/vault_creds`) and enables background token renewal.
- gofr-doc constructs `JwtSecretProvider(vault_client=..., vault_path="gofr/config/jwt-signing-secret")`.
- gofr-doc constructs `token_store, group_store = create_stores_from_env(prefix, vault_client=...)`.
- gofr-doc constructs `AuthService(token_store=..., group_registry=..., secret_provider=..., audience="gofr-api", env_prefix=...)`.
- gofr-doc uses unified Vault auth prefix `gofr/auth` for token/group storage.

## Upgrade steps (recommended order)

### Step 0 - Create a working branch and capture a baseline

In gofr-iq:

1. Create a branch.
2. Run the test suite once and save output.

Commands (from gofr-iq project root):

- `git checkout -b chore/auth-upgrade`
- `./scripts/run_tests.sh`

If you cannot get a clean baseline due to unrelated failures, record the failures. Do not proceed blind.

### Step 1 - Align gofr-common submodule to the gofr-doc version

gofr-iq currently uses an older gofr-common commit than gofr-doc.

1. In gofr-doc, note the gofr-common commit currently used (example observed: `1fc6afd`).
2. In gofr-iq, update `lib/gofr-common` to the same commit.

Commands (from gofr-iq root):

- `cd lib/gofr-common`
- `git fetch --all --tags`
- `git checkout 1fc6afd`
- `cd ../..`
- `git status`

Then update gofr-iq dependencies:

- `uv sync`

Notes:

- This upgrade intentionally removes the idea of multiple backend types for auth storage in gofr-common (memory/file) in favor of Vault-only in real services.
- If gofr-iq relies on file/memory backends in tests, keep those as test doubles at the application layer or update tests to use the gofr-common testing helpers.

### Step 2 - Standardize environment variables (prefix + Vault settings)

Pick one of these options and apply consistently.

Option A (recommended): use GOFR-IQ-prefixed auth env vars everywhere.

- `GOFR_IQ_AUTH_BACKEND=vault`
- `GOFR_IQ_VAULT_URL=http://gofr-vault:8201`
- `GOFR_IQ_VAULT_MOUNT_POINT=secret`
- `GOFR_IQ_VAULT_PATH_PREFIX=gofr/auth`

Option B: keep shared GOFR_* env vars and pass `prefix="GOFR"` into all gofr-common factory calls.

Rationale for Option A:

- Matches the gofr-doc pattern (project-prefixed config via `get_settings(prefix=...)`).
- Avoids accidental cross-project coupling through env var names.
- Still uses shared Vault paths, so shared auth remains shared.

Actions:

1. Update `scripts/gofriq.env` to export the chosen prefix variables.
2. Update docker `.env` generation or runtime exports to set the chosen variables.

Important:

- Do not propagate JWT secrets via env vars.
- The JWT secret is read from Vault at runtime using `JwtSecretProvider`.

### Step 3 - Add gofr-iq AppRole provisioning config (like gofr-doc)

gofr-doc provisions AppRole credentials using gofr-common `setup_approle.py` driven by `config/gofr_approles.json`.

Actions in gofr-iq:

1. Create `config/gofr_approles.json` in gofr-iq, similar to gofr-doc, with roles:
   - `gofr-iq`
   - `gofr-admin-control` (optional but recommended for operator tooling)
2. Add a script `scripts/ensure_approle.sh` that:
   - asserts Vault is running/unsealed
   - reads root token from `secrets/vault_root_token` (or shared gofr-common secrets)
   - runs `uv run lib/gofr-common/scripts/setup_approle.py --project-root ... --config config/gofr_approles.json`
3. Ensure production services mount the generated creds into `/run/secrets/vault_creds`.

Notes:

- gofr-iq currently has `scripts/setup_approle.py` that provisions a different set of services and depends on older policy naming. Treat it as legacy.
- After upgrading gofr-common, prefer the shared `lib/gofr-common/scripts/setup_approle.py` and shared policy naming.

### Step 4 - Update Docker/service wiring to use VaultIdentity creds

Target behavior:

- Every long-running service container that needs auth should have:
  - `/run/secrets/vault_creds` containing RoleID + SecretID JSON
  - env var for Vault address (per chosen prefix)

Actions:

1. For dev container:
   - keep Docker socket mount mechanism as-is (not auth-related)
   - ensure `/run/secrets/vault_creds` exists if you want dev services to behave like prod
2. For prod compose:
   - mount the creds file into each service container at `/run/secrets/vault_creds`

Validation:

- In a running container, `test -f /run/secrets/vault_creds` should succeed.

### Step 5 - Replace GOFR_IQ_JWT_SECRET usage with JwtSecretProvider

This is the core code change.

Actions:

1. In gofr-iq `app/main_mcp.py`:
   - remove the requirement for `GOFR_IQ_JWT_SECRET`.
   - remove the "compare env secret to Vault" logic.
   - create a Vault client using gofr-common factory (`create_vault_client_from_env`).
   - create a `JwtSecretProvider` using that client.
   - create token/group stores using `create_stores_from_env(..., vault_client=...)`.
   - construct `AuthService(..., secret_provider=..., audience="gofr-api")`.

2. In gofr-iq `app/auth/factory.py`:
   - remove the `secret_key` argument from `create_auth_service`.
   - replace it with `secret_provider` wiring.
   - ensure the function accepts `audience` defaulting to `gofr-api`.

3. In gofr-iq `app/main_web.py`:
   - remove the Vault "secret compare" logic entirely.
   - if the web server is healthcheck-only, it can be auth-neutral; otherwise, use the same auth initialization.

4. Ensure `env_prefix` matches your chosen env var scheme (Step 2).

Implementation note:

- In the gofr-doc pattern, the JWT secret provider and the stores share the same Vault client.

### Step 6 - Standardize the Vault auth path prefix to gofr/auth

Actions:

1. Ensure your runtime exports set `*_VAULT_PATH_PREFIX=gofr/auth`.
2. Confirm token/group stores are writing under that prefix.

This is critical for true shared auth across services.

### Step 7 - Align scripts and operator workflow

Actions:

1. If your repo still has local run scripts, remove references to `GOFR_JWT_SECRET` / `GOFR_IQ_JWT_SECRET` as required inputs.
   Prefer Docker-based start/stop entrypoints and the shared gofr-common auth tooling.
2. Update any tooling that currently does:
   - `source lib/gofr-common/scripts/auth_env.sh --docker`
   and expects `GOFR_JWT_SECRET`.

New operator flow should be:

- Use `auth_env.sh` to mint an operator Vault token (`VAULT_TOKEN`) when running admin tooling.
- Use `auth_manager.sh` to create/list groups and tokens.
- Services do not need operator tokens; they use AppRole + VaultIdentity.

### Step 8 - Update tests

Actions:

1. Identify tests that directly set `GOFR_IQ_JWT_SECRET`.
2. Convert them to one of:
   - run with `--no-auth` where auth is not under test
   - use Vault-backed integration tests (preferred when testing auth)
   - use gofr-common testing utilities to create temp tokens/groups

Also ensure tests validate the audience (`gofr-api`) if they create raw JWTs.

### Step 9 - Create scripts/bootstrap_gofr_iq.sh (after auth is aligned)

After Steps 1-8 are complete (gofr-common upgraded, VaultIdentity/AppRole working, JwtSecretProvider in use, Vault path prefix unified, tests updated), add a gofr-iq bootstrap script to replicate what gofr-doc does in `scripts/bootstrap_gofr_doc.sh`.

Goal:

- One guided, idempotent command for operators and developers to bring up prerequisites consistently.

Required responsibilities (match gofr-doc behavior as closely as possible):

1. Initialize git submodules (especially `lib/gofr-common`) if missing.
2. Run the gofr-common platform bootstrap (Vault + Docker network + base image), using the shared scripts under `lib/gofr-common/scripts/`.
3. Build gofr-iq dev and prod images if missing (or when requested via flags).
4. Ensure Vault is running and unsealed.
5. Provision/sync Vault AppRole credentials for gofr-iq and admin-control:
   - call the shared `lib/gofr-common/scripts/setup_approle.py` with `config/gofr_approles.json`
   - ensure credentials land in `secrets/service_creds/`
6. Ensure prod compose mounts the generated creds into `/run/secrets/vault_creds` for each service container.
7. Optionally (flag-controlled) start dev container and/or prod stack at the end.
8. Optionally (flag-controlled) run the test suite via `./scripts/run_tests.sh`.

Notes:

- Keep the script idempotent and self-healing (prefer "check then provision" flow).
- Do not embed secrets in the script or write secrets into docker `.env`.
- Use Docker service names and ports (no localhost assumptions).

### Step 10 - Verification checklist

Run these checks in order:

1. Lint/type checks if present.
2. Targeted auth tests.
3. Full test suite.
4. Dev run:
   - start Vault
   - ensure approle
   - run MCP/MCPO
5. Prod run:
   - `./scripts/start-prod.sh` without needing to export JWT secrets

Commands (examples):

- `./scripts/run_tests.sh -k auth -v`
- `./scripts/run_tests.sh`

## Known pitfalls

- Env prefix mismatch: if you switch to `GOFR_IQ_*` variables but still call gofr-common factories with prefix `GOFR`, auth will silently look in the wrong env vars.
- Missing `/run/secrets/vault_creds`: VaultIdentity will not activate; the code will fall back to env token/AppRole vars. For prod, treat this as a misconfiguration.
- Token/group data location drift: if `*_VAULT_PATH_PREFIX` is not `gofr/auth`, services will create isolated auth islands.
- Audience mismatch: if clients mint tokens without `aud=gofr-api`, verification should fail (by design).

## Suggested "minimal diff" implementation strategy

If you want the smallest possible code delta in gofr-iq:

1. Keep existing `require_auth` toggles and MCP middleware wiring.
2. Replace only the auth initialization block to use `JwtSecretProvider` + `create_vault_client_from_env` + `create_stores_from_env`.
3. Delete all JWT secret env var handling.

That gets you the core security and operational behavior while minimizing churn.
