#!/bin/bash
# Restart all GofrDoc servers in correct order: MCP → MCPO → Web
# All configuration comes from gofr-doc.env with command-line overrides
# Usage: ./restart_servers.sh [--kill-all] [--env PROD|TEST] [--mcp-port PORT] [--mcpo-port PORT] [--web-port PORT]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source centralized configuration (defaults to PROD for this script)
export GOFR_DOC_ENV="${GOFR_DOC_ENV:-PROD}"
source "$SCRIPT_DIR/gofr-doc.env"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            export GOFR_DOC_ENV="$2"
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
        --mcpo-port)
            GOFR_DOC_MCPO_PORT="$2"
            shift 2
            ;;
        --mcpo-host)
            GOFR_DOC_MCPO_HOST="$2"
            shift 2
            ;;
        --web-port)
            GOFR_DOC_WEB_PORT="$2"
            shift 2
            ;;
        --web-host)
            GOFR_DOC_WEB_HOST="$2"
            shift 2
            ;;
        --kill-all)
            KILL_ALL=true
            shift
            ;;
        --help)
            echo "Usage: $(basename "$0") [OPTIONS]"
            echo ""
            echo "OPTIONS:"
            echo "    --env ENV           Environment: PROD or TEST (default: PROD)"
            echo "    --mcp-port PORT     MCP server port (default: $GOFR_DOC_MCP_PORT)"
            echo "    --mcp-host HOST     MCP server host (default: $GOFR_DOC_MCP_HOST)"
            echo "    --mcpo-port PORT    MCPO server port (default: $GOFR_DOC_MCPO_PORT)"
            echo "    --mcpo-host HOST    MCPO server host (default: $GOFR_DOC_MCPO_HOST)"
            echo "    --web-port PORT     Web server port (default: $GOFR_DOC_WEB_PORT)"
            echo "    --web-host HOST     Web server host (default: $GOFR_DOC_WEB_HOST)"
            echo "    --kill-all          Stop all servers without restarting"
            echo "    --help              Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Re-source after GOFR_DOC_ENV may have changed
source "$SCRIPT_DIR/gofr-doc.env"

# Use variables from gofr-doc.env
MCP_PORT="$GOFR_DOC_MCP_PORT"
MCP_HOST="$GOFR_DOC_MCP_HOST"
MCPO_PORT="$GOFR_DOC_MCPO_PORT"
MCPO_HOST="$GOFR_DOC_MCPO_HOST"
WEB_PORT="$GOFR_DOC_WEB_PORT"
WEB_HOST="$GOFR_DOC_WEB_HOST"
TEMPLATES_DIR="$GOFR_DOC_TEMPLATES"
FRAGMENTS_DIR="$GOFR_DOC_FRAGMENTS"
STYLES_DIR="$GOFR_DOC_STYLES"

echo "======================================================================="
echo "GofrDoc Server Restart Script"
echo "Environment: $GOFR_DOC_ENV"
echo "Data Root: $GOFR_DOC_DATA"
echo "======================================================================="

# Kill existing processes
echo ""
echo "Step 1: Stopping existing servers..."
echo "-----------------------------------------------------------------------"

# Function to kill process and wait for it to die
kill_and_wait() {
    local pattern=$1
    local name=$2
    local pids=$(pgrep -f "$pattern")
    
    if [ -z "$pids" ]; then
        echo "  - No $name running"
        return 0
    fi
    
    echo "  Killing $name (PIDs: $pids)..."
    pkill -9 -f "$pattern"
    
    # Wait for processes to die (max 10 seconds)
    for i in {1..20}; do
        if ! pgrep -f "$pattern" >/dev/null 2>&1; then
            echo "  ✓ $name stopped"
            return 0
        fi
        sleep 0.5
    done
    
    echo "  ⚠ Warning: $name may still be running"
    return 1
}

# Kill servers in reverse order (Web, MCPO, MCP)
kill_and_wait "app.main_web" "Web server"
kill_and_wait "mcpo --port" "MCPO wrapper"
kill_and_wait "app.main_mcpo" "MCPO wrapper process"
kill_and_wait "app.main_mcp" "MCP server"

# Wait for ports to be released
echo ""
echo "Waiting for ports to be released..."
sleep 2

# Check if --kill-all flag is set
if [ "$KILL_ALL" = true ]; then
    echo ""
    echo "Kill-all mode: Exiting without restart"
    echo "======================================================================="
    exit 0
fi

# Start MCP server
echo ""
echo "Step 2: Starting MCP server ($MCP_HOST:$MCP_PORT)..."
echo "-----------------------------------------------------------------------"

cd "$GOFR_DOC_ROOT"
nohup uv run python -m app.main_mcp \
    --no-auth \
    --host $MCP_HOST \
    --port $MCP_PORT \
    --templates-dir "$TEMPLATES_DIR" \
    --styles-dir "$STYLES_DIR" \
    --web-url "http://${WEB_HOST}:$WEB_PORT" \
    > "$GOFR_DOC_LOGS/gofr-doc_mcp.log" 2>&1 &

MCP_PID=$!
echo "  MCP server starting (PID: $MCP_PID)"
echo "  Log: $GOFR_DOC_LOGS/gofr-doc_mcp.log"

# Wait for MCP to be ready by checking if it responds to requests
echo "  Waiting for MCP to be ready..."
for i in {1..30}; do
    # MCP requires specific headers, just check if port is responding
    if curl -s -X GET http://localhost:$MCP_PORT/mcp/ \
        -H "Accept: application/json, text/event-stream" \
        2>&1 | grep -q "jsonrpc"; then
        echo "  ✓ MCP server ready"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo "  ✗ ERROR: MCP server failed to start"
        tail -20 "$GOFR_DOC_LOGS/gofr-doc_mcp.log"
        exit 1
    fi
done

# Start MCPO wrapper
echo ""
echo "Step 3: Starting MCPO wrapper ($MCPO_HOST:$MCPO_PORT)..."
echo "-----------------------------------------------------------------------"

nohup uv run python -m app.main_mcpo \
    --no-auth \
    --mcpo-host $MCPO_HOST \
    --mcp-port $MCP_PORT \
    --mcpo-port $MCPO_PORT \
    > "$GOFR_DOC_LOGS/gofr-doc_mcpo.log" 2>&1 &

MCPO_PID=$!
echo "  MCPO wrapper starting (PID: $MCPO_PID)"
echo "  Log: $GOFR_DOC_LOGS/gofr-doc_mcpo.log"

# Wait for MCPO to be ready by checking if the OpenAPI endpoint responds
echo "  Waiting for MCPO to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:$MCPO_PORT/openapi.json 2>&1 | grep -q '"openapi"'; then
        echo "  ✓ MCPO wrapper ready"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo "  ✗ ERROR: MCPO wrapper failed to start"
        tail -20 "$GOFR_DOC_LOGS/gofr-doc_mcpo.log"
        exit 1
    fi
done

# Start Web server
echo ""
echo "Step 4: Starting Web server ($WEB_HOST:$WEB_PORT)..."
echo "-----------------------------------------------------------------------"

nohup uv run python -m app.main_web \
    --no-auth \
    --host $WEB_HOST \
    --port $WEB_PORT \
    --templates-dir "$TEMPLATES_DIR" \
    --fragments-dir "$FRAGMENTS_DIR" \
    --styles-dir "$STYLES_DIR" \
    > "$GOFR_DOC_LOGS/gofr-doc_web.log" 2>&1 &

WEB_PID=$!
echo "  Web server starting (PID: $WEB_PID)"
echo "  Log: $GOFR_DOC_LOGS/gofr-doc_web.log"

# Wait for Web server to be ready by calling ping endpoint
echo "  Waiting for Web server to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:$WEB_PORT/ping 2>&1 | grep -q '"status":"ok"'; then
        echo "  ✓ Web server ready"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo "  ✗ ERROR: Web server failed to start"
        tail -20 "$GOFR_DOC_LOGS/gofr-doc_web.log"
        exit 1
    fi
done

# Summary
echo ""
echo "======================================================================="
echo "All servers started successfully!"
echo "======================================================================="
echo ""
echo "Access URLs:"
echo "  MCP Server:    http://localhost:$MCP_PORT/mcp"
echo "  MCPO Proxy:    http://localhost:$MCPO_PORT"
echo "  Web Server:    http://localhost:$WEB_PORT"
echo ""
echo "Process IDs:"
echo "  MCP:   $MCP_PID"
echo "  MCPO:  $MCPO_PID"
echo "  Web:   $WEB_PID"
echo ""
echo "Logs:"
echo "  MCP:   $GOFR_DOC_LOGS/gofr-doc_mcp.log"
echo "  MCPO:  $GOFR_DOC_LOGS/gofr-doc_mcpo.log"
echo "  Web:   $GOFR_DOC_LOGS/gofr-doc_web.log"
echo ""
echo "To stop all servers: $0 --kill-all"
echo "To view logs: tail -f $GOFR_DOC_LOGS/gofr-doc_*.log"
echo "======================================================================="
