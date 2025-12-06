#!/bin/bash
# Run MCPO wrapper without authentication (no-auth/public mode)
# All configuration comes from gofr-doc.env with command-line overrides

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/gofr-doc.env"

# Parse command line arguments for overrides
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            GOFR_DOC_MCPO_PORT="$2"
            shift 2
            ;;
        --host)
            GOFR_DOC_MCPO_HOST="$2"
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
        --env)
            export GOFR_DOC_ENV="$2"
            source "$SCRIPT_DIR/gofr-doc.env"
            shift 2
            ;;
        --help)
            echo "Usage: $(basename "$0") [OPTIONS]"
            echo ""
            echo "OPTIONS:"
            echo "    --port PORT       MCPO server port (default: $GOFR_DOC_MCPO_PORT)"
            echo "    --host HOST       MCPO server host (default: $GOFR_DOC_MCPO_HOST)"
            echo "    --mcp-port PORT   MCP server port (default: $GOFR_DOC_MCP_PORT)"
            echo "    --mcp-host HOST   MCP server host (default: $GOFR_DOC_MCP_HOST)"
            echo "    --env ENV         Environment: PROD or TEST (default: $GOFR_DOC_ENV)"
            echo "    --help            Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

cd "$GOFR_DOC_ROOT"

# Configuration from env vars (with possible overrides)
MCPO_PORT="$GOFR_DOC_MCPO_PORT"
MCPO_HOST="$GOFR_DOC_MCPO_HOST"
MCP_PORT="$GOFR_DOC_MCP_PORT"
MCP_HOST="${GOFR_DOC_MCP_HOST:-localhost}"
LOG_FILE="$GOFR_DOC_LOGS/mcpo_server.log"

# Wait for MCP server to be available
echo "Checking if MCP server is ready at http://${MCP_HOST}:${MCP_PORT}..."
for i in {1..30}; do
    if curl -s -o /dev/null -w "%{http_code}" http://${MCP_HOST}:${MCP_PORT}/ | grep -q "200\|404\|405"; then
        echo "✓ MCP server is available"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ MCP server not available after 15 seconds"
        echo "Please start MCP server first: bash scripts/run_mcp.sh"
        exit 1
    fi
    sleep 0.5
done

# Kill any existing MCPO server on this port
echo "Stopping any existing MCPO server on port $MCPO_PORT..."
pkill -f "main_mcpo.*--port $MCPO_PORT" 2>/dev/null
pkill -f "python.*main_mcpo.py" 2>/dev/null
sleep 1

# Start MCPO server in no-auth mode
echo "Starting MCPO server in no-auth mode..."
echo "  Host: $MCPO_HOST"
echo "  Port: $MCPO_PORT"
MCP_URL="http://${MCP_HOST}:${MCP_PORT}/mcp"
uv tool run mcpo \
    --host "$MCPO_HOST" \
    --port "$MCPO_PORT" \
    --server-type "streamable-http" \
    -- "$MCP_URL" \
    > "$LOG_FILE" 2>&1 &

MCPO_PID=$!

# Wait for server to start
echo "Waiting for MCPO server to start (PID: $MCPO_PID)..."
for i in {1..20}; do
    if curl -s http://localhost:$MCPO_PORT/openapi.json > /dev/null 2>&1; then
        echo ""
        echo "✓ MCPO server is ready on $MCPO_HOST:$MCPO_PORT (no-auth mode)"
        echo "  Log file: $LOG_FILE"
        echo "  PID: $MCPO_PID"
        echo ""
        echo "=== Connection URLs ==="
        echo "  Local OpenAPI:     http://localhost:${MCPO_PORT}/openapi.json"
        echo "  Network OpenAPI:   http://$(hostname):${MCPO_PORT}/openapi.json"
        echo "  Swagger UI:        http://localhost:${MCPO_PORT}/docs"
        echo "  Network Swagger:   http://$(hostname):${MCPO_PORT}/docs"
        echo ""
        echo "=== Backend Servers ==="
        echo "  MCP Server:        http://${MCP_HOST}:${MCP_PORT}"
        echo ""
        echo "=== For OpenWebUI ==="
        echo "  Use this URL:      http://$(hostname):${MCPO_PORT}"
        echo ""
        exit 0
    fi
    sleep 0.5
done

# If we get here, server failed to start
echo "✗ MCPO server failed to start within 10 seconds"
echo "Check log file: $LOG_FILE"
cat "$LOG_FILE"
exit 1
