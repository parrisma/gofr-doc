#!/bin/bash
# Run MCP server without authentication (no-auth mode)
# All configuration comes from gofr-doc.env with command-line overrides

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/gofr-doc.env"

# Parse command line arguments for overrides
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            GOFR_DOC_MCP_PORT="$2"
            shift 2
            ;;
        --host)
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
            echo "    --port PORT    MCP server port (default: $GOFR_DOC_MCP_PORT)"
            echo "    --host HOST    MCP server host (default: $GOFR_DOC_MCP_HOST)"
            echo "    --env ENV      Environment: PROD or TEST (default: $GOFR_DOC_ENV)"
            echo "    --help         Show this help message"
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
PORT="$GOFR_DOC_MCP_PORT"
HOST="$GOFR_DOC_MCP_HOST"
TEMPLATES_DIR="$GOFR_DOC_TEMPLATES"
STYLES_DIR="$GOFR_DOC_STYLES"
LOG_FILE="$GOFR_DOC_LOGS/mcp_server.log"

# Kill any existing MCP server on this port
echo "Stopping any existing MCP server on port $PORT..."
pkill -f "main_mcp.*--port $PORT" 2>/dev/null
pkill -f "python.*main_mcp.py" 2>/dev/null
sleep 1

# Start MCP server in no-auth mode with HTTP transport (URL mode)
echo "Starting MCP server in no-auth mode with HTTP transport..."
echo "  Host: $HOST"
echo "  Port: $PORT"
uv run python -m app.main_mcp \
    --no-auth \
    --host "$HOST" \
    --port "$PORT" \
    --transport http \
    --templates-dir "$TEMPLATES_DIR" \
    --styles-dir "$STYLES_DIR" \
    --web-url "http://${GOFR_DOC_WEB_HOST}:${GOFR_DOC_WEB_PORT}" \
    --proxy-url-mode "url" \
    > "$LOG_FILE" 2>&1 &

MCP_PID=$!

# Wait for server to start
echo "Waiting for MCP server to start (PID: $MCP_PID)..."
sleep 2
for i in {1..20}; do
    if kill -0 $MCP_PID 2>/dev/null && curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/ | grep -q "200\|404\|405"; then
        echo ""
        echo "✓ MCP server is ready on $HOST:$PORT (no-auth mode)"
        echo "  Log file: $LOG_FILE"
        echo "  PID: $MCP_PID"
        echo "  Templates: $TEMPLATES_DIR"
        echo "  Styles: $STYLES_DIR"
        echo ""
        echo "=== Connection URLs ==="
        echo "  Local:    http://localhost:$PORT"
        echo "  Network:  http://$(hostname):$PORT"
        echo "  Protocol: MCP (JSON-RPC over HTTP)"
        echo ""
        exit 0
    fi
    sleep 0.5
done

# If we get here, server failed to start
echo "✗ MCP server failed to start within 10 seconds"
echo "Check log file: $LOG_FILE"
cat "$LOG_FILE"
exit 1
