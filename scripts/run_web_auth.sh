#!/bin/bash
# Run Web server with authentication enabled for testing
# Uses test JWT secret and token store that matches conftest.py configuration

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/gofr_doc.env"
cd "$GOFR_DOC_ROOT"

# Configuration (matches conftest.py TEST_JWT_SECRET and TEST_TOKEN_STORE_PATH)
export GOFR_DOC_ENV=TEST
JWT_SECRET="test-secret-key-for-secure-testing-do-not-use-in-production"
TOKEN_STORE="$GOFR_DOC_TOKEN_STORE"
TEMPLATES_DIR="$GOFR_DOC_TEMPLATES"
FRAGMENTS_DIR="$GOFR_DOC_FRAGMENTS"
STYLES_DIR="$GOFR_DOC_STYLES"
PORT="$GOFR_DOC_WEB_PORT"
LOG_FILE="$GOFR_DOC_LOGS/web_test_server.log"

# Kill any existing web server on this port
echo "Stopping any existing web server on port $PORT..."
pkill -f "main_web.*--port $PORT" 2>/dev/null
sleep 1

# Start Web server with auth
echo "Starting Web server with authentication..."
uv run python -m app.main_web \
    --port "$PORT" \
    --jwt-secret "$JWT_SECRET" \
    --token-store "$TOKEN_STORE" \
    --templates-dir "$TEMPLATES_DIR" \
    --fragments-dir "$FRAGMENTS_DIR" \
    --styles-dir "$STYLES_DIR" \
    > "$LOG_FILE" 2>&1 &

WEB_PID=$!

# Wait for server to start
echo "Waiting for web server to start (PID: $WEB_PID)..."
for i in {1..10}; do
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo "✓ Web server is ready on port $PORT"
        echo "  Log file: $LOG_FILE"
        echo "  PID: $WEB_PID"
        exit 0
    fi
    sleep 0.5
done

# If we get here, server failed to start
echo "✗ Web server failed to start within 5 seconds"
echo "Check log file: $LOG_FILE"
cat "$LOG_FILE"
exit 1
