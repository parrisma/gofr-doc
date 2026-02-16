#!/bin/bash
# =============================================================================
# Migrate secrets into Docker volumes
# =============================================================================
# Copies existing secrets from lib/gofr-common/secrets/ into both the
# gofr-secrets (prod/dev) and gofr-secrets-test (tests) Docker volumes.
#
# These volumes are SHARED across all GOFR projects (gofr-dig, gofr-doc, etc).
#
# Run once from the host (or dev container with Docker socket access):
#   ./scripts/migrate_secrets_to_volume.sh
#
# Safe to re-run — overwrites volume contents with latest from source dir.
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SOURCE_DIR="$PROJECT_ROOT/lib/gofr-common/secrets"
PROJECT_CREDS_DIR="$PROJECT_ROOT/secrets/service_creds"

# Both volumes to seed (shared across all GOFR projects)
VOLUMES=("gofr-secrets" "gofr-secrets-test")

# ---- Helpers ----------------------------------------------------------------
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
err()   { echo -e "\033[1;31m[FAIL]\033[0m  $*" >&2; }

# ---- Verify source exists ---------------------------------------------------
if [ ! -d "$SOURCE_DIR" ] || [ ! -f "$SOURCE_DIR/vault_root_token" ]; then
    err "Source secrets not found at $SOURCE_DIR"
    echo "  Expected: vault_root_token, vault_unseal_key, bootstrap_tokens.json, service_creds/"
    exit 1
fi

# If this project has generated/updated service creds in $PROJECT_ROOT/secrets,
# overlay them on top of the gofr-common secrets dir before seeding the volumes.
# This ensures the shared volumes always contain the latest role_id/secret_id
# for gofr-doc without requiring manual copying into the submodule tree.
TMP_SECRETS_DIR=""
cleanup_tmp() {
    if [ -n "${TMP_SECRETS_DIR:-}" ] && [ -d "${TMP_SECRETS_DIR}" ]; then
        rm -rf "${TMP_SECRETS_DIR}" || true
    fi
}
trap cleanup_tmp EXIT

TMP_SECRETS_DIR="$(mktemp -d)"
cp -a "$SOURCE_DIR/." "$TMP_SECRETS_DIR/"

if [ -d "$PROJECT_CREDS_DIR" ]; then
    mkdir -p "$TMP_SECRETS_DIR/service_creds"
    cp -a "$PROJECT_CREDS_DIR/." "$TMP_SECRETS_DIR/service_creds/"
fi

info "Source directory: $SOURCE_DIR"
info "Staging directory: $TMP_SECRETS_DIR"
echo "  Contents:"
ls -la "$TMP_SECRETS_DIR/" | sed 's/^/    /'
echo ""

# ---- Seed each volume -------------------------------------------------------
for VOLUME in "${VOLUMES[@]}"; do
    # Ensure volume exists
    if ! docker volume inspect "$VOLUME" >/dev/null 2>&1; then
        info "Creating volume: $VOLUME"
        docker volume create "$VOLUME"
    fi

    info "Copying secrets into volume $VOLUME ..."

    # Start a disposable Alpine container with the volume mounted
    HELPER="gofr-secrets-migrate-$$"
    docker run -d --name "$HELPER" -v "$VOLUME:/dst" alpine:3.19 sleep 60 >/dev/null

    # Copy from the calling container's filesystem into the helper
    docker cp "$TMP_SECRETS_DIR/." "$HELPER:/dst/"

    # Fix permissions inside the volume
    # All GOFR containers use UID 1000 / GID 1000 — set ownership to match
    docker exec "$HELPER" sh -c '
        chown -R 1000:1000 /dst
        chmod 700 /dst
        chmod 600 /dst/vault_root_token /dst/vault_unseal_key 2>/dev/null || true
        chmod 600 /dst/service_creds/*.json 2>/dev/null || true
        echo "  Contents of volume:"
        ls -la /dst/ | sed "s/^/    /"
        if [ -d /dst/service_creds ]; then
            echo "  Service creds:"
            ls -la /dst/service_creds/ | sed "s/^/    /"
        fi
    '

    docker rm -f "$HELPER" >/dev/null 2>&1

    ok "Volume '$VOLUME' seeded successfully."
    echo ""
done

ok "Both volumes seeded. Verify with:"
echo "  docker run --rm -v gofr-secrets:/s:ro alpine ls -la /s/"
echo "  docker run --rm -v gofr-secrets-test:/s:ro alpine ls -la /s/"
