#!/bin/bash
# Run MCP server with authentication enabled for testing
# Uses test JWT secret and token store that matches conftest.py configuration

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/gofr_doc.env"
cd "$GOFR_DOC_ROOT"

# Configuration (matches conftest.py TEST_JWT_SECRET and TEST_TOKEN_STORE_PATH)
export GOFR_DOC_ENV=TEST
JWT_SECRET="test-secret-key-for-secure-testing-do-not-use-in-production"
TOKEN_STORE="$GOFR_DOC_TOKEN_STORE"
TEMPLATES_DIR="$GOFR_DOC_TEMPLATES"
STYLES_DIR="$GOFR_DOC_STYLES"
PORT="$GOFR_DOC_MCP_PORT"
LOG_FILE="$GOFR_DOC_LOGS/mcp_test_server.log"

# Kill any existing MCP server on this port
echo "Stopping any existing MCP server on port $PORT..."
pkill -f "main_mcp.*--port $PORT" 2>/dev/null
sleep 1

# Start MCP server with auth
echo "Starting MCP server with authentication..."
uv run python -m app.main_mcp \
    --port "$PORT" \
    --jwt-secret "$JWT_SECRET" \
    --token-store "$TOKEN_STORE" \
    --templates-dir "$TEMPLATES_DIR" \
    --styles-dir "$STYLES_DIR" \
    --web-url "http://172.22.9.172:8012" \
    --proxy-url-mode "url" \
    > "$LOG_FILE" 2>&1 &

MCP_PID=$!

# Wait for server to start
echo "Waiting for MCP server to start (PID: $MCP_PID)..."
for i in {1..10}; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo "✓ MCP server is ready on port $PORT"
        echo "  Log file: $LOG_FILE"
        echo "  PID: $MCP_PID"
        exit 0
    fi
    sleep 0.5
done

# If we get here, server failed to start
echo "✗ MCP server failed to start within 5 seconds"
echo "Check log file: $LOG_FILE"
cat "$LOG_FILE"
exit 1
