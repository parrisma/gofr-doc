#!/bin/bash
# GOFR-DOC Server Restart Script
# Wrapper for the shared restart_servers.sh script
#
# Usage: ./restart_servers.sh [OPTIONS]
#
# Options:
#   --env PROD|TEST     Environment: PROD or TEST (default: PROD)
#   --mcp-port PORT     MCP server port
#   --mcp-host HOST     MCP server host
#   --mcpo-port PORT    MCPO server port
#   --mcpo-host HOST    MCPO server host
#   --web-port PORT     Web server port
#   --web-host HOST     Web server host
#   --kill-all          Stop all servers without restarting
#   --help              Show this help message

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON_SCRIPTS="$SCRIPT_DIR/../../gofr-common/scripts"

# Check for lib/gofr-common location first (inside container)
if [ -d "$SCRIPT_DIR/../lib/gofr-common/scripts" ]; then
    COMMON_SCRIPTS="$SCRIPT_DIR/../lib/gofr-common/scripts"
fi

# Source centralized configuration (defaults to PROD for restart script)
export GOFR_DOC_ENV="${GOFR_DOC_ENV:-PROD}"
source "$SCRIPT_DIR/gofr-doc.env"

# Parse command line arguments
PASSTHROUGH_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            export GOFR_DOC_ENV="$2"
            shift 2
            ;;
        --mcp-port)
            GOFR_DOC_MCP_PORT="$2"
            shift 2
            ;;
        --mcp-host)
            GOFR_DOC_MCP_HOST="$2"
            shift 2
            ;;
        --mcpo-port)
            GOFR_DOC_MCPO_PORT="$2"
            shift 2
            ;;
        --mcpo-host)
            GOFR_DOC_MCPO_HOST="$2"
            shift 2
            ;;
        --web-port)
            GOFR_DOC_WEB_PORT="$2"
            shift 2
            ;;
        --web-host)
            GOFR_DOC_WEB_HOST="$2"
            shift 2
            ;;
        --kill-all|--help)
            PASSTHROUGH_ARGS+=("$1")
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Re-source after GOFR_DOC_ENV may have changed
source "$SCRIPT_DIR/gofr-doc.env"

# Map project-specific vars to common vars
export GOFR_PROJECT_NAME="gofr-doc"
export GOFR_PROJECT_ROOT="$GOFR_DOC_ROOT"
export GOFR_LOGS_DIR="$GOFR_DOC_LOGS"
export GOFR_DATA_DIR="$GOFR_DOC_DATA"
export GOFR_ENV="$GOFR_DOC_ENV"
export GOFR_MCP_PORT="$GOFR_DOC_MCP_PORT"
export GOFR_MCPO_PORT="$GOFR_DOC_MCPO_PORT"
export GOFR_WEB_PORT="$GOFR_DOC_WEB_PORT"
export GOFR_MCP_HOST="$GOFR_DOC_MCP_HOST"
export GOFR_MCPO_HOST="$GOFR_DOC_MCPO_HOST"
export GOFR_WEB_HOST="$GOFR_DOC_WEB_HOST"
export GOFR_NETWORK="$GOFR_DOC_NETWORK"

# JWT authentication credentials (shared across all gofr services)
export GOFR_JWT_SECRET="${GOFR_JWT_SECRET:-}"
export GOFR_TOKEN_STORE="${GOFR_DOC_TOKEN_STORE:-}"

# Extra args for MCP server (project-specific)
export GOFR_MCP_EXTRA_ARGS="--templates-dir $GOFR_DOC_TEMPLATES --styles-dir $GOFR_DOC_STYLES"

# Call shared script
source "$COMMON_SCRIPTS/restart_servers.sh" "${PASSTHROUGH_ARGS[@]}"
