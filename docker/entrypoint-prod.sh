#!/bin/bash
set -e

# =======================================================================
# GOFR-DOC Production Entrypoint
# Runs MCP, MCPO, and Web servers using supervisor
# =======================================================================

# Configuration from environment (with defaults)
export GOFR_DOC_MCP_PORT="${GOFR_DOC_MCP_PORT:-8040}"
export GOFR_DOC_MCPO_PORT="${GOFR_DOC_MCPO_PORT:-8041}"
export GOFR_DOC_WEB_PORT="${GOFR_DOC_WEB_PORT:-8042}"
export GOFR_JWT_SECRET="${GOFR_JWT_SECRET:?GOFR_JWT_SECRET is required}"
export GOFR_DOC_AUTH_BACKEND="${GOFR_DOC_AUTH_BACKEND:-vault}"
export GOFR_DOC_VAULT_URL="${GOFR_DOC_VAULT_URL:-http://gofr-vault:8201}"
export GOFR_DOC_VAULT_TOKEN="${GOFR_DOC_VAULT_TOKEN:-}"
export GOFR_DOC_STORAGE_DIR="${GOFR_DOC_STORAGE_DIR:-/home/gofr-doc/data/storage}"
export GOFR_DOC_SESSIONS_DIR="${GOFR_DOC_SESSIONS_DIR:-/home/gofr-doc/data/sessions}"
export GOFR_DOC_TEMPLATES_DIR="${GOFR_DOC_TEMPLATES_DIR:-/home/gofr-doc/data/templates}"
export GOFR_DOC_FRAGMENTS_DIR="${GOFR_DOC_FRAGMENTS_DIR:-/home/gofr-doc/data/fragments}"
export GOFR_DOC_STYLES_DIR="${GOFR_DOC_STYLES_DIR:-/home/gofr-doc/data/styles}"
export GOFR_DOC_LOG_LEVEL="${GOFR_DOC_LOG_LEVEL:-INFO}"

# -----------------------------------------------------------------------
# Vault AppRole runtime identity (required)
# -----------------------------------------------------------------------
# gofr-common prefers AppRole creds injected at /run/secrets/vault_creds.
# We mount the shared secrets volume at /run/gofr-secrets and copy the
# project-specific creds file into the standard location.
CREDS_SRC="/run/gofr-secrets/service_creds/gofr-doc.json"
CREDS_DST_DIR="/run/secrets"
CREDS_DST="${CREDS_DST_DIR}/vault_creds"

if [ ! -f "${CREDS_SRC}" ]; then
	echo "[ERR] Missing Vault AppRole creds at ${CREDS_SRC}" >&2
	echo "[ERR] Fix: run ./scripts/ensure_approle.sh then ./scripts/migrate_secrets_to_volume.sh" >&2
	exit 1
fi

mkdir -p "${CREDS_DST_DIR}"
cp "${CREDS_SRC}" "${CREDS_DST}"
chmod 600 "${CREDS_DST}"
chown gofr-doc:gofr-doc "${CREDS_DST}" || true

# Ensure directories exist
mkdir -p /home/gofr-doc/data/storage
mkdir -p /home/gofr-doc/data/sessions
mkdir -p /home/gofr-doc/logs

echo "======================================================================="
echo "GOFR-DOC Production Server Starting"
echo "======================================================================="
echo "MCP Port:     ${GOFR_DOC_MCP_PORT}"
echo "MCPO Port:    ${GOFR_DOC_MCPO_PORT}"
echo "Web Port:     ${GOFR_DOC_WEB_PORT}"
echo "Auth Backend: ${GOFR_DOC_AUTH_BACKEND}"
echo "Vault URL:    ${GOFR_DOC_VAULT_URL:-not set}"
echo "Storage:      ${GOFR_DOC_STORAGE_DIR}"
echo "Sessions:     ${GOFR_DOC_SESSIONS_DIR}"
echo "Log Level:    ${GOFR_DOC_LOG_LEVEL}"
echo "======================================================================="

# Generate supervisor config
VENV_BIN="/home/gofr-doc/.venv/bin"

cat > /tmp/supervisord.conf << EOF
[supervisord]
nodaemon=true
logfile=/home/gofr-doc/logs/supervisord.log
pidfile=/tmp/supervisord.pid
loglevel=info

[program:mcp]
command=${VENV_BIN}/python -m app.main_mcp --port ${GOFR_DOC_MCP_PORT} --jwt-secret "${GOFR_JWT_SECRET}" --templates-dir "${GOFR_DOC_TEMPLATES_DIR}" --styles-dir "${GOFR_DOC_STYLES_DIR}" --web-url "http://localhost:${GOFR_DOC_WEB_PORT}"
directory=/home/gofr-doc
environment=PYTHONPATH="/home/gofr-doc",PATH="${VENV_BIN}:%(ENV_PATH)s",GOFR_DOC_AUTH_BACKEND="${GOFR_DOC_AUTH_BACKEND}",GOFR_DOC_VAULT_URL="${GOFR_DOC_VAULT_URL}",GOFR_DOC_VAULT_TOKEN="${GOFR_DOC_VAULT_TOKEN}"
autostart=true
autorestart=true
stdout_logfile=/home/gofr-doc/logs/mcp.log
stderr_logfile=/home/gofr-doc/logs/mcp_error.log
priority=10

[program:web]
command=${VENV_BIN}/python -m app.main_web --port ${GOFR_DOC_WEB_PORT} --jwt-secret "${GOFR_JWT_SECRET}" --templates-dir "${GOFR_DOC_TEMPLATES_DIR}" --fragments-dir "${GOFR_DOC_FRAGMENTS_DIR}" --styles-dir "${GOFR_DOC_STYLES_DIR}"
directory=/home/gofr-doc
environment=PYTHONPATH="/home/gofr-doc",PATH="${VENV_BIN}:%(ENV_PATH)s",GOFR_DOC_AUTH_BACKEND="${GOFR_DOC_AUTH_BACKEND}",GOFR_DOC_VAULT_URL="${GOFR_DOC_VAULT_URL}",GOFR_DOC_VAULT_TOKEN="${GOFR_DOC_VAULT_TOKEN}"
autostart=true
autorestart=true
stdout_logfile=/home/gofr-doc/logs/web.log
stderr_logfile=/home/gofr-doc/logs/web_error.log
priority=20

[program:mcpo]
command=${VENV_BIN}/mcpo --port ${GOFR_DOC_MCPO_PORT} --server-type streamable-http -- http://localhost:${GOFR_DOC_MCP_PORT}/mcp
directory=/home/gofr-doc
environment=PATH="${VENV_BIN}:%(ENV_PATH)s"
autostart=true
autorestart=true
startsecs=5
stdout_logfile=/home/gofr-doc/logs/mcpo.log
stderr_logfile=/home/gofr-doc/logs/mcpo_error.log
priority=30
EOF

# Run supervisor
exec supervisord -c /tmp/supervisord.conf
