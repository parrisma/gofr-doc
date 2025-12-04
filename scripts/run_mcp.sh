#!/bin/bash
# Run MCP server without authentication (no-auth mode)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/gofr_doc.env"
cd "$GOFR_DOC_ROOT"

# Configuration for no-auth mode
export GOFR_DOC_ENV=TEST
TEMPLATES_DIR="$GOFR_DOC_TEMPLATES"
STYLES_DIR="$GOFR_DOC_STYLES"
PORT="$GOFR_DOC_MCP_PORT"
LOG_FILE="$GOFR_DOC_LOGS/mcp_server.log"

# Kill any existing MCP server on this port
echo "Stopping any existing MCP server on port $PORT..."
pkill -f "main_mcp.*--port $PORT" 2>/dev/null
pkill -f "python.*main_mcp.py" 2>/dev/null
sleep 1

# Start MCP server in no-auth mode with HTTP transport (URL mode)
echo "Starting MCP server in no-auth mode with HTTP transport..."
uv run python -m app.main_mcp \
    --no-auth \
    --port "$PORT" \
    --transport http \
    --templates-dir "$TEMPLATES_DIR" \
    --styles-dir "$STYLES_DIR" \
    --web-url "http://172.22.9.172:8012" \
    --proxy-url-mode "url" \
    > "$LOG_FILE" 2>&1 &

MCP_PID=$!

# Wait for server to start
echo "Waiting for MCP server to start (PID: $MCP_PID)..."
sleep 2  # Give server time to bind to port and start uvicorn
for i in {1..20}; do
    # Test if server is responding (check if process is running and server responds)
    if kill -0 $MCP_PID 2>/dev/null && curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/ | grep -q "200\|404\|405"; then
        echo ""
        echo "✓ MCP server is ready on port $PORT (no-auth mode)"
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
