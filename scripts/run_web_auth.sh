#!/bin/bash
# Run Web server with authentication enabled for testing
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
JWT_SECRET="test-secret-key-for-secure-testing-do-not-use-in-production"
TOKEN_STORE="$GOFR_DOC_TOKEN_STORE"
TEMPLATES_DIR="$GOFR_DOC_TEMPLATES"
FRAGMENTS_DIR="$GOFR_DOC_FRAGMENTS"
STYLES_DIR="$GOFR_DOC_STYLES"
LOG_FILE="$GOFR_DOC_LOGS/web_test_server.log"

# Kill any existing web server on this port
echo "Stopping any existing web server on port $PORT..."
pkill -f "main_web.*--port $PORT" 2>/dev/null
sleep 1

# Start Web server with auth
echo "Starting Web server with authentication..."
echo "  Host: $HOST"
echo "  Port: $PORT"
uv run python -m app.main_web \
    --host "$HOST" \
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
        echo "✓ Web server is ready on $HOST:$PORT"
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
