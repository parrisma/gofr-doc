#!/bin/bash
# Run Web server without authentication (no-auth mode)
# All configuration comes from gofr-doc.env with command-line overrides

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/gofr-doc.env"

# Parse command line arguments for overrides
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            GOFR_DOC_WEB_PORT="$2"
            shift 2
            ;;
        --host)
            GOFR_DOC_WEB_HOST="$2"
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
            echo "    --port PORT    Web server port (default: $GOFR_DOC_WEB_PORT)"
            echo "    --host HOST    Web server host (default: $GOFR_DOC_WEB_HOST)"
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
PORT="$GOFR_DOC_WEB_PORT"
HOST="$GOFR_DOC_WEB_HOST"
TEMPLATES_DIR="$GOFR_DOC_TEMPLATES"
FRAGMENTS_DIR="$GOFR_DOC_FRAGMENTS"
STYLES_DIR="$GOFR_DOC_STYLES"
LOG_FILE="$GOFR_DOC_LOGS/web_server.log"

# Kill any existing web server on this port
echo "Stopping any existing web server on port $PORT..."
pkill -f "main_web.*--port $PORT" 2>/dev/null
pkill -f "python.*main_web.py" 2>/dev/null
sleep 1

# Start web server in no-auth mode
echo "Starting web server in no-auth mode..."
echo "  Host: $HOST"
echo "  Port: $PORT"
uv run python -m app.main_web \
    --no-auth \
    --host "$HOST" \
    --port "$PORT" \
    --templates-dir "$TEMPLATES_DIR" \
    --fragments-dir "$FRAGMENTS_DIR" \
    --styles-dir "$STYLES_DIR" \
    > "$LOG_FILE" 2>&1 &

WEB_PID=$!

# Wait for server to start
echo "Waiting for web server to start (PID: $WEB_PID)..."
for i in {1..20}; do
    if curl -s http://localhost:$PORT/ping > /dev/null 2>&1; then
        echo ""
        echo "✓ Web server is ready on $HOST:$PORT (no-auth mode)"
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
