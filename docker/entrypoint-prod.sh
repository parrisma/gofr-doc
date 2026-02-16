#!/bin/bash
# =============================================================================
# gofr-doc Production Entrypoint
# Common startup for all gofr-doc containers: copies AppRole creds,
# sets up directories, then exec's CMD.
#
# JWT signing secret is read from Vault at runtime by JwtSecretProvider
# (no env var needed).
#
# Usage in compose.prod.yml:
#   entrypoint: ["/home/gofr-doc/entrypoint-prod.sh"]
#   command: ["/home/gofr-doc/.venv/bin/python", "-m", "app.main_mcp", ...]
#
# Environment variables:
#   GOFR_DOC_VAULT_URL    - Vault address (default: http://gofr-vault:<GOFR_VAULT_PORT>)
#   GOFR_DOC_DATA_DIR     - Data root (default: /home/gofr-doc/data)
#   GOFR_DOC_STORAGE_DIR  - Storage dir (default: /home/gofr-doc/data/storage)
#   GOFR_DOC_NO_AUTH      - Set to "1" to disable authentication
# =============================================================================
set -e

VENV_PATH="/home/gofr-doc/.venv"
CREDS_SOURCE="/run/gofr-secrets/service_creds/gofr-doc.json"
CREDS_TARGET="/run/secrets/vault_creds"

# --- Directories -------------------------------------------------------------
DATA_DIR="${GOFR_DOC_DATA_DIR:-/home/gofr-doc/data}"
STORAGE_DIR="${GOFR_DOC_STORAGE_DIR:-/home/gofr-doc/data/storage}"
mkdir -p "${DATA_DIR}" "${STORAGE_DIR}" /home/gofr-doc/data/sessions /home/gofr-doc/logs
chown -R gofr-doc:gofr-doc /home/gofr-doc/data /home/gofr-doc/logs 2>/dev/null || true

# --- Deploy built-in content into the data volume ----------------------------
# _content/ is baked into the image (outside the volume mount).
# Copy into the data volume so templates/styles/fragments/images are available.
#
# INTERIM: Long-term, replace this with a dedicated content-init container
# (same pattern as vault-init) that populates the data volume independently.
# This keeps the app image small as content grows in size and number.
CONTENT_STAGE="/home/gofr-doc/_content"
for subdir in templates styles fragments images; do
    src="${CONTENT_STAGE}/${subdir}"
    dst="${DATA_DIR}/${subdir}"
    if [ -d "${src}" ]; then
        # Merge: copy new/updated files without removing user additions
        cp -a "${src}/." "${dst}/" 2>/dev/null || cp -r "${src}/." "${dst}/"
        chown -R gofr-doc:gofr-doc "${dst}" 2>/dev/null || true
        echo "Deployed built-in ${subdir} to ${dst}"
    fi
done

# --- Copy AppRole credentials ------------------------------------------------
mkdir -p /run/secrets
if [ -f "${CREDS_SOURCE}" ]; then
    cp "${CREDS_SOURCE}" "${CREDS_TARGET}"
    chown gofr-doc:gofr-doc "${CREDS_TARGET}"
else
    echo "WARNING: No AppRole credentials at ${CREDS_SOURCE}"
fi

# --- Auth flag ---------------------------------------------------------------
EXTRA_ARGS=""
if [ "${GOFR_DOC_NO_AUTH:-}" = "1" ]; then
    echo "WARNING: Authentication is DISABLED (GOFR_DOC_NO_AUTH=1)"
    EXTRA_ARGS="--no-auth"
fi

# --- Exec the service command ------------------------------------------------
# Drop to gofr-doc user and exec the CMD passed by compose
exec su -s /bin/bash gofr-doc -c "exec $* ${EXTRA_ARGS}"
