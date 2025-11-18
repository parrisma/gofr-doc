#!/bin/bash
# Run Web server without authentication (no-auth mode)

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Configuration for no-auth mode
TEMPLATES_DIR="test/render/data/docs/templates"
FRAGMENTS_DIR="test/render/data/docs/fragments"
STYLES_DIR="test/render/data/docs/styles"
PORT=8010
LOG_FILE="/tmp/web_server.log"

# Kill any existing web server on this port
echo "Stopping any existing web server on port $PORT..."
pkill -f "main_web.*--port $PORT" 2>/dev/null
pkill -f "python.*main_web.py" 2>/dev/null
sleep 1

# Start web server in no-auth mode
echo "Starting web server in no-auth mode..."
uv run python -m app.main_web \
    --no-auth \
    --port "$PORT" \
    --templates-dir "$TEMPLATES_DIR" \
    --fragments-dir "$FRAGMENTS_DIR" \
    --styles-dir "$STYLES_DIR" \
    > "$LOG_FILE" 2>&1 &

WEB_PID=$!

# Wait for server to start
echo "Waiting for web server to start (PID: $WEB_PID)..."
for i in {1..20}; do
    # Test if server is responding
    if curl -s http://localhost:$PORT/ping > /dev/null 2>&1; then
        echo ""
        echo "✓ Web server is ready on port $PORT (no-auth mode)"
        echo "  Log file: $LOG_FILE"
        echo "  PID: $WEB_PID"
        echo "  Templates: $TEMPLATES_DIR"
        echo "  Fragments: $FRAGMENTS_DIR"
        echo "  Styles: $STYLES_DIR"
        echo ""
        echo "=== Connection URLs ==="
        echo "  Local:    http://localhost:$PORT"
        echo "  Network:  http://$(hostname):$PORT"
        echo "  Proxy:    http://localhost:$PORT/proxy/{guid}"
        echo ""
        exit 0
    fi
    sleep 0.5
done

# If we get here, server failed to start
echo "✗ Web server failed to start within 10 seconds"
echo "Check log file: $LOG_FILE"
cat "$LOG_FILE"
exit 1
