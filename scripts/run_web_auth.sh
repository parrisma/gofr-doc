#!/bin/bash
# Run Web server with authentication enabled for testing
# Uses test JWT secret and token store that matches conftest.py configuration

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Configuration (matches conftest.py TEST_JWT_SECRET and TEST_TOKEN_STORE_PATH)
JWT_SECRET="test-secret-key-for-secure-testing-do-not-use-in-production"
TOKEN_STORE="/tmp/doco_test_tokens.json"
TEMPLATES_DIR="test/render/data/docs/templates"
FRAGMENTS_DIR="test/render/data/docs/fragments"
STYLES_DIR="test/render/data/docs/styles"
PORT=8012
LOG_FILE="/tmp/web_test_server.log"

# Kill any existing web server on this port
echo "Stopping any existing web server on port $PORT..."
pkill -f "main_web.*--port $PORT" 2>/dev/null
sleep 1

# Start web server with auth
echo "Starting web server with authentication..."
python -m app.main_web \
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
