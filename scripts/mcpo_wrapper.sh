#!/bin/bash
# MCPO Wrapper Script for gofr-doc MCP Server
# Provides convenient wrapper for starting MCPO proxy in various modes
# All configuration comes from gofr-doc.env with command-line overrides

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/gofr-doc.env"

# Default configuration from env vars
MODE="${GOFR_DOC_MCPO_MODE:-public}"
MCP_PORT="${GOFR_DOC_MCP_PORT}"
MCPO_PORT="${GOFR_DOC_MCPO_PORT}"
MCPO_HOST="${GOFR_DOC_MCPO_HOST}"
MCPO_API_KEY="${GOFR_DOC_MCPO_API_KEY:-changeme}"
MCP_HOST="${GOFR_DOC_MCP_HOST:-localhost}"

# Help message
show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Start MCPO proxy for gofr-doc MCP server

OPTIONS:
    --mode MODE          Authentication mode: 'auth' or 'public' (default: public)
    --mcp-port PORT      MCP server port (default: 8000)
    --mcpo-port PORT     MCPO proxy port (default: 8001)
    --api-key KEY        MCPO API key for Open WebUI (default: changeme)
    --jwt-token TOKEN    JWT token for MCP server auth (required for auth mode)
    --help               Show this help message

ENVIRONMENT VARIABLES:
    GOFR_DOC_MCPO_MODE       Authentication mode: 'auth' or 'public'
    GOFR_DOC_MCP_PORT        MCP server port
    GOFR_DOC_MCPO_PORT       MCPO proxy port
    GOFR_DOC_MCPO_API_KEY    MCPO API key
    GOFR_DOC_JWT_TOKEN       JWT token for authenticated mode
    GOFR_DOC_MCP_HOST        MCP server host (default: localhost)

EXAMPLES:
    # Start in public mode (no authentication)
    $(basename "$0")

    # Start in authenticated mode
    $(basename "$0") --mode auth --jwt-token "your-jwt-token"

    # Start with custom ports
    $(basename "$0") --mcp-port 8000 --mcpo-port 8001

    # Using environment variables
    export GOFR_DOC_MCPO_MODE=auth
    export GOFR_DOC_JWT_TOKEN="your-jwt-token"
    $(basename "$0")

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --mcp-port)
            MCP_PORT="$2"
            shift 2
            ;;
        --mcpo-port)
            MCPO_PORT="$2"
            shift 2
            ;;
        --api-key)
            MCPO_API_KEY="$2"
            shift 2
            ;;
        --jwt-token)
            GOFR_DOC_JWT_TOKEN="$2"
            shift 2
            ;;
        --mcp-host)
            MCP_HOST="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate mode
if [[ "$MODE" != "auth" && "$MODE" != "public" ]]; then
    echo "ERROR: Invalid mode '$MODE'. Must be 'auth' or 'public'"
    exit 1
fi

# Build MCP URL
MCP_URL="http://${MCP_HOST}:${MCP_PORT}/mcp"

# Start MCPO based on mode
case "$MODE" in
    auth)
        echo "Starting MCPO wrapper in AUTHENTICATED mode"
        
        if [ -z "$GOFR_DOC_JWT_TOKEN" ]; then
            echo "ERROR: GOFR_DOC_JWT_TOKEN required for auth mode"
            echo "Set via --jwt-token argument or GOFR_DOC_JWT_TOKEN environment variable"
            exit 1
        fi
        
        echo "  MCP Server: $MCP_URL"
        echo "  MCPO Port: $MCPO_PORT"
        echo "  OpenAPI Docs: http://localhost:${MCPO_PORT}/docs"
        echo ""
        
        uv tool run mcpo \
            --port "$MCPO_PORT" \
            --api-key "$MCPO_API_KEY" \
            --server-type "streamable-http" \
            --header "{\"Authorization\": \"Bearer $GOFR_DOC_JWT_TOKEN\"}" \
            -- "$MCP_URL"
        ;;
        
    public)
        echo "Starting MCPO wrapper in PUBLIC mode (no authentication)"
        echo "  MCP Server: $MCP_URL"
        echo "  MCPO Port: $MCPO_PORT"
        echo "  OpenAPI Docs: http://localhost:${MCPO_PORT}/docs"
        echo ""
        
        uv tool run mcpo \
            --port "$MCPO_PORT" \
            --api-key "$MCPO_API_KEY" \
            --server-type "streamable-http" \
            -- "$MCP_URL"
        ;;
esac
