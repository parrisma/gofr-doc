# Bootstrap Implementation Plan — gofr-doc

Mirrors gofr-dig's `scripts/bootstrap_gofr_dig.sh` pattern.
Universal, idempotent bootstrap for any developer or CI environment.

## Steps

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Add `gofr-doc-policy` to gofr-common `policies.py` | ✅ Done | Adds `POLICY_DOC_READ` + `gofr-doc-policy` |
| 2 | Create `config/gofr_approles.json` | ✅ Done | Roles: `gofr-doc`, `gofr-admin-control` |
| 3 | Create `scripts/ensure_approle.sh` | ✅ Done | Self-healing: sync vs full provision |
| 4 | Create `scripts/migrate_secrets_to_volume.sh` | ✅ Done | Seeds `gofr-secrets` + `gofr-secrets-test` |
| 5 | Create `scripts/bootstrap_gofr_doc.sh` | ✅ Done | Main bootstrap script (gofr-dig style) |
| 6 | Update compose files for secrets volume | ✅ Done | `docker/compose.prod.yml` mounts `gofr-secrets` at `/run/gofr-secrets:ro` |
| 7 | Update entrypoint-prod.sh for AppRole creds | ✅ Done | Copies `/run/gofr-secrets/service_creds/gofr-doc.json` → `/run/secrets/vault_creds` |
| 8 | Test end-to-end | ✅ Done | `./scripts/bootstrap_gofr_doc.sh --yes --auto-tests` |
| 9 | Run full test suite | ✅ Done | 571 passed (via bootstrap `--auto-tests`) |
| 10 | Git commit | ⬜ TODO | Single commit for bootstrap work |

## Architecture Decisions

1. **AppRole always** — no dev-token fallback. gofr-doc uses AppRole creds like gofr-dig.
2. **Shared secrets volume** — `gofr-secrets` and `gofr-secrets-test` are external Docker volumes shared across all GOFR projects. Not project-specific.
3. **Policy name** — `gofr-doc-policy` (new, added to gofr-common `POLICIES` dict).
4. **Service user UID** — 1000:1000, matching GOFR convention.
5. **Secrets flow** — Volume mounted read-only at `/run/gofr-secrets:ro`, entrypoint copies `service_creds/gofr-doc.json` → `/run/secrets/vault_creds` at startup.

## File Inventory

```
config/gofr_approles.json           # NEW — AppRole roles + policies config
scripts/bootstrap_gofr_doc.sh       # NEW — Main bootstrap script
scripts/ensure_approle.sh           # NEW — AppRole provisioning wrapper
scripts/migrate_secrets_to_volume.sh # NEW — Seed Docker secrets volumes
docker/compose.dev.yml              # UPDATE — add gofr-secrets-test volume mount
docker/compose.prod.yml             # UPDATE — add gofr-secrets volume mount (prod)
docker/entrypoint-prod.sh           # UPDATE — copy AppRole creds from volume
lib/gofr-common/.../policies.py     # UPDATE — add gofr-doc-policy
```

## Progress Log

- 2026-02-16: Completed steps 1–4 (policy + AppRole config + ensure_approle + volume seeding script).
- 2026-02-16: Completed step 5 (added `scripts/bootstrap_gofr_doc.sh`).
- 2026-02-16: Wired AppRole runtime creds for dev/prod containers (entrypoints + run scripts). Tests remain on dev-mode Vault token (matches gofr-dig test runner pattern).
- 2026-02-16: Updated production Docker Compose stack to use shared secrets volume + AppRole identity.
- 2026-02-16: Ran bootstrap end-to-end + full test suite: 571 passed, 0 failed, 0 skipped.
