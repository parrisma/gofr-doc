#!/bin/bash
# =============================================================================
# gofr-doc Production Entrypoint
# Common startup for all gofr-doc containers: copies AppRole creds, reads
# JWT signing secret from Vault, sets up directories, then exec's CMD.
#
# Usage in compose.prod.yml:
#   entrypoint: ["/home/gofr-doc/entrypoint-prod.sh"]
#   command: ["/home/gofr-doc/.venv/bin/python", "-m", "app.main_mcp", ...]
#
# Environment variables:
#   GOFR_JWT_SECRET       - Override: skip Vault read, use this value directly
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

# --- Copy AppRole credentials ------------------------------------------------
mkdir -p /run/secrets
if [ -f "${CREDS_SOURCE}" ]; then
    cp "${CREDS_SOURCE}" "${CREDS_TARGET}"
    chown gofr-doc:gofr-doc "${CREDS_TARGET}"
else
    echo "WARNING: No AppRole credentials at ${CREDS_SOURCE}"
fi

# --- Read JWT secret from Vault via AppRole ----------------------------------
# Source of truth: Vault at secret/gofr/config/jwt-signing-secret
# Env var GOFR_JWT_SECRET is a fallback override only.
if [ -z "${GOFR_JWT_SECRET:-}" ]; then
    if [ -f "${CREDS_TARGET}" ]; then
        echo "Reading JWT secret from Vault via AppRole..."
        VAULT_URL="${GOFR_DOC_VAULT_URL:-http://gofr-vault:${GOFR_VAULT_PORT:-8201}}"
        JWT_FROM_VAULT=$(
            su -s /bin/bash gofr-doc -c "${VENV_PATH}/bin/python -c \"
import json, sys, os
sys.path.insert(0, '/home/gofr-doc')
from gofr_common.auth.backends.vault_config import VaultConfig
from gofr_common.auth.backends.vault_client import VaultClient
creds = json.load(open('${CREDS_TARGET}'))
config = VaultConfig(url='${VAULT_URL}', role_id=creds['role_id'], secret_id=creds['secret_id'])
client = VaultClient(config)
secret = client.read_secret('gofr/config/jwt-signing-secret')
print(secret['value'])
\"" 2>&1
        ) || true

        if [ -n "${JWT_FROM_VAULT}" ]; then
            export GOFR_JWT_SECRET="${JWT_FROM_VAULT}"
            echo "JWT secret loaded from Vault via AppRole"
        else
            echo "FATAL: Cannot read JWT secret from Vault and GOFR_JWT_SECRET not set"
            exit 1
        fi
    else
        echo "FATAL: No Vault credentials at ${CREDS_TARGET} and GOFR_JWT_SECRET not set"
        exit 1
    fi
else
    echo "JWT secret set via environment override"
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
