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
export GOFR_DOC_JWT_SECRET="${GOFR_DOC_JWT_SECRET:?JWT_SECRET is required}"
export GOFR_DOC_TOKEN_STORE="${GOFR_DOC_TOKEN_STORE:-/home/gofr-doc/data/auth/tokens.json}"
export GOFR_DOC_STORAGE_DIR="${GOFR_DOC_STORAGE_DIR:-/home/gofr-doc/data/storage}"
export GOFR_DOC_SESSIONS_DIR="${GOFR_DOC_SESSIONS_DIR:-/home/gofr-doc/data/sessions}"
export GOFR_DOC_TEMPLATES_DIR="${GOFR_DOC_TEMPLATES_DIR:-/home/gofr-doc/config/templates}"
export GOFR_DOC_FRAGMENTS_DIR="${GOFR_DOC_FRAGMENTS_DIR:-/home/gofr-doc/config/fragments}"
export GOFR_DOC_STYLES_DIR="${GOFR_DOC_STYLES_DIR:-/home/gofr-doc/config/styles}"
export GOFR_DOC_LOG_LEVEL="${GOFR_DOC_LOG_LEVEL:-INFO}"

# Ensure directories exist
mkdir -p /home/gofr-doc/data/storage
mkdir -p /home/gofr-doc/data/auth
mkdir -p /home/gofr-doc/data/sessions
mkdir -p /home/gofr-doc/logs

# Initialize empty token store if it doesn't exist
if [ ! -f "${GOFR_DOC_TOKEN_STORE}" ]; then
    echo '{"tokens": {}}' > "${GOFR_DOC_TOKEN_STORE}"
fi

echo "======================================================================="
echo "GOFR-DOC Production Server Starting"
echo "======================================================================="
echo "MCP Port:     ${GOFR_DOC_MCP_PORT}"
echo "MCPO Port:    ${GOFR_DOC_MCPO_PORT}"
echo "Web Port:     ${GOFR_DOC_WEB_PORT}"
echo "Storage:      ${GOFR_DOC_STORAGE_DIR}"
echo "Sessions:     ${GOFR_DOC_SESSIONS_DIR}"
echo "Token Store:  ${GOFR_DOC_TOKEN_STORE}"
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
command=${VENV_BIN}/python -m app.main_mcp --port ${GOFR_DOC_MCP_PORT} --jwt-secret "${GOFR_DOC_JWT_SECRET}" --token-store "${GOFR_DOC_TOKEN_STORE}" --templates-dir "${GOFR_DOC_TEMPLATES_DIR}" --styles-dir "${GOFR_DOC_STYLES_DIR}" --web-url "http://localhost:${GOFR_DOC_WEB_PORT}"
directory=/home/gofr-doc
environment=PYTHONPATH="/home/gofr-doc",PATH="${VENV_BIN}:%(ENV_PATH)s"
autostart=true
autorestart=true
stdout_logfile=/home/gofr-doc/logs/mcp.log
stderr_logfile=/home/gofr-doc/logs/mcp_error.log
priority=10

[program:web]
command=${VENV_BIN}/python -m app.main_web --port ${GOFR_DOC_WEB_PORT} --jwt-secret "${GOFR_DOC_JWT_SECRET}" --token-store "${GOFR_DOC_TOKEN_STORE}" --templates-dir "${GOFR_DOC_TEMPLATES_DIR}" --fragments-dir "${GOFR_DOC_FRAGMENTS_DIR}" --styles-dir "${GOFR_DOC_STYLES_DIR}"
directory=/home/gofr-doc
environment=PYTHONPATH="/home/gofr-doc",PATH="${VENV_BIN}:%(ENV_PATH)s"
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
