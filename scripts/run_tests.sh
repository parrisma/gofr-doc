#!/bin/bash
# Test runner script with consistent configuration
# This script:
# - Sets consistent JWT secret for all test components
# - Configures test ports for MCP and web servers
# - Points to test data directories
# - Starts servers if needed for integration tests
# - Runs pytest with proper configuration

set -e  # Exit on error

# Test configuration constants
export DOCO_JWT_SECRET="test-secret-key-for-secure-testing-do-not-use-in-production"
export DOCO_TOKEN_STORE="/tmp/doco_test_tokens.json"
export DOCO_MCP_PORT="8011"
export DOCO_WEB_PORT="8010"

# Test data directories (relative to project root)
TEST_DATA_ROOT="test/render/data/docs"
TEMPLATES_DIR="${TEST_DATA_ROOT}/templates"
FRAGMENTS_DIR="${TEST_DATA_ROOT}/fragments"
STYLES_DIR="${TEST_DATA_ROOT}/styles"
STORAGE_DIR="test/render/data/storage"

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== DOCO Test Runner ===${NC}"
echo "Project root: ${PROJECT_ROOT}"
echo "JWT Secret: ${DOCO_JWT_SECRET:0:20}..."
echo "MCP Port: ${DOCO_MCP_PORT}"
echo "Web Port: ${DOCO_WEB_PORT}"
echo "Templates: ${TEMPLATES_DIR}"
echo "Fragments: ${FRAGMENTS_DIR}"
echo "Styles: ${STYLES_DIR}"
echo ""

# Kill any leftover servers from previous test runs
echo -e "${YELLOW}Cleaning up any previous test servers...${NC}"
pkill -9 -f "python.*main_mcp.py" 2>/dev/null || true
pkill -9 -f "python.*main_web.py" 2>/dev/null || true
sleep 1

# Purge sessions and storage from previous test runs
echo -e "${YELLOW}Purging sessions and storage from previous runs...${NC}"
python scripts/storage_manager.py purge --age-days=0 --yes 2>/dev/null || echo "  (storage purge skipped - no existing data)"
# Clear all sessions in data/sessions directory
if [ -d "data/sessions" ]; then
    rm -f data/sessions/*.json 2>/dev/null || true
    echo "  Cleared sessions directory"
fi
# Clear test token store
rm -f "${DOCO_TOKEN_STORE}" 2>/dev/null || true
echo -e "${GREEN}Cleanup complete${NC}"
echo ""

# Function to check if port is in use
port_in_use() {
    local port=$1
    if command -v lsof &> /dev/null; then
        lsof -i :"${port}" &> /dev/null
    elif command -v ss &> /dev/null; then
        ss -tuln | grep -q ":${port} "
    elif command -v netstat &> /dev/null; then
        netstat -tuln | grep -q ":${port} "
    else
        # Fallback: try to connect
        timeout 1 bash -c "cat < /dev/null > /dev/tcp/127.0.0.1/${port}" 2>/dev/null
    fi
}

# Function to start MCP server for integration tests
start_mcp_server() {
    echo -e "${YELLOW}Starting MCP server on port ${DOCO_MCP_PORT}...${NC}"
    
    if port_in_use "${DOCO_MCP_PORT}"; then
        echo -e "${YELLOW}Port ${DOCO_MCP_PORT} already in use, killing existing process...${NC}"
        pkill -9 -f "python.*main_mcp.py" || true
        sleep 2
    fi
    
    nohup python app/main_mcp.py \
        --port="${DOCO_MCP_PORT}" \
        --templates-dir="${TEMPLATES_DIR}" \
        --styles-dir="${STYLES_DIR}" \
        > /tmp/mcp_server_test.log 2>&1 &
    
    local MCP_PID=$!
    echo "MCP Server PID: ${MCP_PID}"
    
    # Wait for server to be ready
    echo -n "Waiting for MCP server to start"
    for i in {1..30}; do
        if port_in_use "${DOCO_MCP_PORT}"; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 0.5
    done
    
    echo -e " ${RED}✗${NC}"
    echo -e "${RED}Failed to start MCP server${NC}"
    echo "Last 20 lines of server log:"
    tail -20 /tmp/mcp_server_test.log
    return 1
}

# Function to start web server for integration tests
start_web_server() {
    echo -e "${YELLOW}Starting web server on port ${DOCO_WEB_PORT}...${NC}"
    
    if port_in_use "${DOCO_WEB_PORT}"; then
        echo -e "${YELLOW}Port ${DOCO_WEB_PORT} already in use, killing existing process...${NC}"
        pkill -9 -f "python.*main_web.py" || true
        sleep 2
    fi
    
    nohup python app/main_web.py \
        --port="${DOCO_WEB_PORT}" \
        --templates-dir="${TEMPLATES_DIR}" \
        --fragments-dir="${FRAGMENTS_DIR}" \
        --styles-dir="${STYLES_DIR}" \
        > /tmp/web_server_test.log 2>&1 &
    
    local WEB_PID=$!
    echo "Web Server PID: ${WEB_PID}"
    
    # Wait for server to be ready
    echo -n "Waiting for web server to start"
    for i in {1..30}; do
        if port_in_use "${DOCO_WEB_PORT}"; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 0.5
    done
    
    echo -e " ${RED}✗${NC}"
    echo -e "${RED}Failed to start web server${NC}"
    echo "Last 20 lines of server log:"
    tail -20 /tmp/web_server_test.log
    return 1
}

# Function to stop servers
stop_servers() {
    echo -e "${YELLOW}Stopping test servers...${NC}"
    pkill -9 -f "python.*main_mcp.py" 2>/dev/null || true
    pkill -9 -f "python.*main_web.py" 2>/dev/null || true
    sleep 1
    echo -e "${GREEN}Servers stopped${NC}"
}

# Parse command line arguments
START_SERVERS=false
STOP_ONLY=false
PYTEST_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --with-servers|--start-servers)
            START_SERVERS=true
            shift
            ;;
        --stop|--stop-servers)
            STOP_ONLY=true
            shift
            ;;
        *)
            PYTEST_ARGS+=("$1")
            shift
            ;;
    esac
done

# Handle stop-only mode
if [ "$STOP_ONLY" = true ]; then
    stop_servers
    exit 0
fi

# Start servers if requested
if [ "$START_SERVERS" = true ]; then
    echo -e "${GREEN}=== Starting Test Servers ===${NC}"
    start_mcp_server || exit 1
    start_web_server || exit 1
    echo ""
fi

# Run pytest
echo -e "${GREEN}=== Running Tests ===${NC}"
if [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
    # Default: run all tests
    python -m pytest test/ -v
else
    # Run with custom arguments
    python -m pytest "${PYTEST_ARGS[@]}"
fi

TEST_EXIT_CODE=$?

# Stop servers if we started them
if [ "$START_SERVERS" = true ]; then
    echo ""
    stop_servers
fi

# Report results
echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=== Tests Passed ===${NC}"
else
    echo -e "${RED}=== Tests Failed (exit code: ${TEST_EXIT_CODE}) ===${NC}"
    if [ "$START_SERVERS" = true ]; then
        echo ""
        echo "Server logs available at:"
        echo "  MCP: /tmp/mcp_server_test.log"
        echo "  Web: /tmp/web_server_test.log"
    fi
fi

exit $TEST_EXIT_CODE
