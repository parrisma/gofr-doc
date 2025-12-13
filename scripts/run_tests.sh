#!/bin/bash
# =============================================================================
# GOFR-Doc Test Runner
# =============================================================================
# Standardized test runner script with consistent configuration across all
# GOFR projects. This script:
# - Sets up virtual environment and PYTHONPATH
# - Configures test ports for MCP and Web servers
# - Supports coverage reporting
# - Supports Docker execution
# - Supports test categories (unit, integration, all)
# - Manages server lifecycle for integration tests
#
# Usage:
#   ./scripts/run_tests.sh                          # Run all tests
#   ./scripts/run_tests.sh test/mcp/                # Run specific test directory
#   ./scripts/run_tests.sh -k "doc"                 # Run tests matching keyword
#   ./scripts/run_tests.sh -v                       # Run with verbose output
#   ./scripts/run_tests.sh --coverage               # Run with coverage report
#   ./scripts/run_tests.sh --coverage-html          # Run with HTML coverage report
#   ./scripts/run_tests.sh --docker                 # Run tests in Docker container
#   ./scripts/run_tests.sh --unit                   # Run unit tests only (no servers)
#   ./scripts/run_tests.sh --integration            # Run integration tests (with servers)
#   ./scripts/run_tests.sh --no-servers             # Run without starting servers
#   ./scripts/run_tests.sh --stop                   # Stop servers only
#   ./scripts/run_tests.sh --cleanup-only           # Clean environment only
# =============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# =============================================================================
# CONFIGURATION
# =============================================================================

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project-specific configuration
PROJECT_NAME="gofr-doc"
ENV_PREFIX="GOFR_DOC"
CONTAINER_NAME="gofr-doc-dev"
TEST_DIR="test"
COVERAGE_SOURCE="app"
LOG_DIR="${PROJECT_ROOT}/logs"

# Activate virtual environment
VENV_DIR="${PROJECT_ROOT}/.venv"
if [ -f "${VENV_DIR}/bin/activate" ]; then
    source "${VENV_DIR}/bin/activate"
    echo "Activated venv: ${VENV_DIR}"
else
    echo -e "${YELLOW}Warning: Virtual environment not found at ${VENV_DIR}${NC}"
fi

# Source centralized port configuration from gofr-common
if [ -d "${PROJECT_ROOT}/lib/gofr-common/config" ]; then
    source "${PROJECT_ROOT}/lib/gofr-common/config/gofr_ports.sh"
elif [ -d "${PROJECT_ROOT}/../gofr-common/config" ]; then
    source "${PROJECT_ROOT}/../gofr-common/config/gofr_ports.sh"
fi

# Source centralized environment configuration
export GOFR_DOC_ENV="TEST"
if [ -f "${SCRIPT_DIR}/gofr-doc.env" ]; then
    source "${SCRIPT_DIR}/gofr-doc.env"
fi

# Set up PYTHONPATH for gofr-common discovery
if [ -d "${PROJECT_ROOT}/lib/gofr-common/src" ]; then
    export PYTHONPATH="${PROJECT_ROOT}:${PROJECT_ROOT}/lib/gofr-common/src:${PYTHONPATH:-}"
elif [ -d "${PROJECT_ROOT}/../gofr-common/src" ]; then
    export PYTHONPATH="${PROJECT_ROOT}:${PROJECT_ROOT}/../gofr-common/src:${PYTHONPATH:-}"
else
    export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
fi

# Test configuration
export GOFR_DOC_JWT_SECRET="test-secret-key-for-secure-testing-do-not-use-in-production"
export GOFR_DOC_TOKEN_STORE="${GOFR_DOC_TOKEN_STORE:-${LOG_DIR}/${PROJECT_NAME}_tokens_test.json}"
# Ports are now set by gofr_ports.sh (8040, 8041, 8042)

# Ensure directories exist
mkdir -p "${LOG_DIR}"
mkdir -p "${GOFR_DOC_STORAGE:-${PROJECT_ROOT}/data/storage}"
mkdir -p "${GOFR_DOC_TEMPLATES:-${PROJECT_ROOT}/data/templates}"
mkdir -p "${GOFR_DOC_FRAGMENTS:-${PROJECT_ROOT}/data/fragments}"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

print_header() {
    echo -e "${GREEN}=== ${PROJECT_NAME} Test Runner ===${NC}"
    echo "Project root: ${PROJECT_ROOT}"
    echo "Environment: ${GOFR_DOC_ENV}"
    echo "JWT Secret: ${GOFR_DOC_JWT_SECRET:0:20}..."
    echo "Token store: ${GOFR_DOC_TOKEN_STORE}"
    echo "MCP Port: ${GOFR_DOC_MCP_PORT}"
    echo "Web Port: ${GOFR_DOC_WEB_PORT}"
    echo ""
}

port_in_use() {
    local port=$1
    if command -v lsof >/dev/null 2>&1; then
        lsof -i ":${port}" >/dev/null 2>&1
    elif command -v ss >/dev/null 2>&1; then
        ss -tuln | grep -q ":${port} "
    elif command -v netstat >/dev/null 2>&1; then
        netstat -tuln | grep -q ":${port} "
    else
        timeout 1 bash -c "cat < /dev/null > /dev/tcp/127.0.0.1/${port}" >/dev/null 2>&1
    fi
}

free_port() {
    local port=$1
    if ! port_in_use "$port"; then
        return 0
    fi
    if command -v lsof >/dev/null 2>&1; then
        lsof -ti ":${port}" | xargs -r kill -9 2>/dev/null || true
    elif command -v ss >/dev/null 2>&1; then
        ss -lptn "sport = :${port}" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d'=' -f2 | xargs -r kill -9 2>/dev/null || true
    fi
    sleep 1
}

stop_servers() {
    echo "Stopping server processes..."
    pkill -9 -f "python.*main_mcp" 2>/dev/null || true
    pkill -9 -f "python.*main_web" 2>/dev/null || true
    sleep 2
    
    if ps aux | grep -E "python.*(main_mcp|main_web)" | grep -v grep >/dev/null 2>&1; then
        echo -e "${RED}WARNING: Some server processes still running${NC}"
        return 1
    fi
    echo "All server processes stopped"
    return 0
}

cleanup_environment() {
    echo -e "${YELLOW}Cleaning up test environment...${NC}"
    
    # Use restart_servers.sh to stop all servers
    if [ -f "${SCRIPT_DIR}/restart_servers.sh" ]; then
        "${SCRIPT_DIR}/restart_servers.sh" --kill-all 2>/dev/null || true
    else
        # Fallback to manual cleanup
        stop_servers || true
    fi
    
    # Empty token store
    echo "{}" > "${GOFR_DOC_TOKEN_STORE}" 2>/dev/null || true
    echo "Token store emptied: ${GOFR_DOC_TOKEN_STORE}"
    
    # Clean up sessions
    rm -f data/sessions/*.json 2>/dev/null || true
    
    echo -e "${GREEN}Cleanup complete${NC}"
}

start_mcp_server() {
    local log_file="${LOG_DIR}/${PROJECT_NAME}_mcp_test.log"
    echo -e "${YELLOW}Starting MCP server on port ${GOFR_DOC_MCP_PORT}...${NC}"
    
    free_port "${GOFR_DOC_MCP_PORT}"
    rm -f "${log_file}"

    nohup uv run python app/main_mcp.py \
        --port "${GOFR_DOC_MCP_PORT}" \
        --jwt-secret "${GOFR_DOC_JWT_SECRET}" \
        --token-store "${GOFR_DOC_TOKEN_STORE}" \
        > "${log_file}" 2>&1 &
    MCP_PID=$!
    echo "MCP PID: ${MCP_PID}"

    echo -n "Waiting for MCP server"
    for _ in {1..30}; do
        if ! kill -0 ${MCP_PID} 2>/dev/null; then
            echo -e " ${RED}✗${NC}"
            tail -20 "${log_file}"
            return 1
        fi
        if port_in_use "${GOFR_DOC_MCP_PORT}"; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 0.5
    done
    echo -e " ${RED}✗${NC}"
    tail -20 "${log_file}"
    return 1
}

start_web_server() {
    local log_file="${LOG_DIR}/${PROJECT_NAME}_web_test.log"
    echo -e "${YELLOW}Starting Web server on port ${GOFR_DOC_WEB_PORT}...${NC}"
    
    free_port "${GOFR_DOC_WEB_PORT}"
    rm -f "${log_file}"

    nohup uv run python app/main_web.py \
        --port "${GOFR_DOC_WEB_PORT}" \
        --jwt-secret "${GOFR_DOC_JWT_SECRET}" \
        --token-store "${GOFR_DOC_TOKEN_STORE}" \
        > "${log_file}" 2>&1 &
    WEB_PID=$!
    echo "Web PID: ${WEB_PID}"

    echo -n "Waiting for Web server"
    for _ in {1..30}; do
        if ! kill -0 ${WEB_PID} 2>/dev/null; then
            echo -e " ${RED}✗${NC}"
            tail -20 "${log_file}"
            return 1
        fi
        if port_in_use "${GOFR_DOC_WEB_PORT}"; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 0.5
    done
    echo -e " ${RED}✗${NC}"
    tail -20 "${log_file}"
    return 1
}

# =============================================================================
# ARGUMENT PARSING
# =============================================================================

USE_DOCKER=false
START_SERVERS=true
COVERAGE=false
COVERAGE_HTML=false
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_ALL=false
STOP_ONLY=false
CLEANUP_ONLY=false
PYTEST_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --coverage|--cov)
            COVERAGE=true
            shift
            ;;
        --coverage-html)
            COVERAGE=true
            COVERAGE_HTML=true
            shift
            ;;
        --unit)
            RUN_UNIT=true
            START_SERVERS=false
            shift
            ;;
        --integration)
            RUN_INTEGRATION=true
            START_SERVERS=true
            shift
            ;;
        --all)
            RUN_ALL=true
            START_SERVERS=true
            shift
            ;;
        --no-servers|--without-servers)
            START_SERVERS=false
            shift
            ;;
        --with-servers|--start-servers)
            START_SERVERS=true
            shift
            ;;
        --stop|--stop-servers)
            STOP_ONLY=true
            shift
            ;;
        --cleanup-only)
            CLEANUP_ONLY=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [PYTEST_ARGS...]"
            echo ""
            echo "Options:"
            echo "  --docker         Run tests inside Docker container"
            echo "  --coverage       Run with coverage report"
            echo "  --coverage-html  Run with HTML coverage report"
            echo "  --unit           Run unit tests only (no servers)"
            echo "  --integration    Run integration tests (with servers)"
            echo "  --all            Run all test categories"
            echo "  --no-servers     Don't start test servers"
            echo "  --with-servers   Start test servers (default)"
            echo "  --stop           Stop servers and exit"
            echo "  --cleanup-only   Clean environment and exit"
            echo "  --help, -h       Show this help message"
            exit 0
            ;;
        *)
            PYTEST_ARGS+=("$1")
            shift
            ;;
    esac
done

# =============================================================================
# MAIN EXECUTION
# =============================================================================

print_header

# Handle stop-only mode
if [ "$STOP_ONLY" = true ]; then
    echo -e "${YELLOW}Stopping servers and exiting...${NC}"
    if [ -f "${SCRIPT_DIR}/restart_servers.sh" ]; then
        "${SCRIPT_DIR}/restart_servers.sh" --kill-all
    else
        stop_servers
    fi
    exit 0
fi

# Handle cleanup-only mode
if [ "$CLEANUP_ONLY" = true ]; then
    cleanup_environment
    exit 0
fi

# Clean up before starting
cleanup_environment

# Initialize token store
if [ ! -f "${GOFR_DOC_TOKEN_STORE}" ]; then
    echo "{}" > "${GOFR_DOC_TOKEN_STORE}"
fi

# Start servers if needed (using centralized restart_servers.sh)
MCP_PID=""
WEB_PID=""
if [ "$START_SERVERS" = true ]; then
    echo -e "${GREEN}=== Starting Test Servers ===${NC}"
    
    if [ "$USE_DOCKER" = true ]; then
        # Start servers inside Docker container
        echo -e "${YELLOW}Starting servers in Docker container ${CONTAINER_NAME}...${NC}"
        docker exec "${CONTAINER_NAME}" bash -c "cd /home/gofr/devroot/${PROJECT_NAME}/scripts && \
            GOFR_DOC_ENV=TEST \
            GOFR_DOC_JWT_SECRET='${GOFR_DOC_JWT_SECRET}' \
            GOFR_DOC_TOKEN_STORE='${GOFR_DOC_TOKEN_STORE}' \
            ./restart_servers.sh --env TEST --mcp-port ${GOFR_DOC_MCP_PORT} --web-port ${GOFR_DOC_WEB_PORT} --mcpo-port ${GOFR_DOC_MCPO_PORT}" || {
            echo -e "${RED}Failed to start servers in Docker${NC}"
            exit 1
        }
        echo -e "${GREEN}Servers started successfully in Docker${NC}"
    else
        # Use the centralized restart_servers.sh script for local execution
        if [ -f "${SCRIPT_DIR}/restart_servers.sh" ]; then
            # Force kill any existing servers and restart
            "${SCRIPT_DIR}/restart_servers.sh" --kill-all || true
            sleep 2
            
            # Start servers with TEST environment and authentication
            GOFR_DOC_ENV=TEST \
            GOFR_DOC_JWT_SECRET="${GOFR_DOC_JWT_SECRET}" \
            GOFR_DOC_TOKEN_STORE="${GOFR_DOC_TOKEN_STORE}" \
            "${SCRIPT_DIR}/restart_servers.sh" \
                --env TEST \
                --mcp-port "${GOFR_DOC_MCP_PORT}" \
                --web-port "${GOFR_DOC_WEB_PORT}" \
                --mcpo-port "${GOFR_DOC_MCPO_PORT}" || {
                echo -e "${RED}Failed to start servers${NC}"
                exit 1
            }
            echo -e "${GREEN}Servers started successfully${NC}"
        else
            echo -e "${RED}ERROR: restart_servers.sh not found${NC}"
            exit 1
        fi
    fi
    echo ""
fi

# Build coverage arguments
COVERAGE_ARGS=""
if [ "$COVERAGE" = true ]; then
    COVERAGE_ARGS="--cov=${COVERAGE_SOURCE} --cov-report=term-missing"
    if [ "$COVERAGE_HTML" = true ]; then
        COVERAGE_ARGS="${COVERAGE_ARGS} --cov-report=html:htmlcov"
    fi
    echo -e "${BLUE}Coverage reporting enabled${NC}"
fi

# =============================================================================
# RUN TESTS
# =============================================================================

echo -e "${GREEN}=== Running Tests ===${NC}"
set +e
TEST_EXIT_CODE=0

if [ "$USE_DOCKER" = true ]; then
    # Docker execution
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${RED}Container ${CONTAINER_NAME} is not running.${NC}"
        echo "Run: ./docker/run-dev.sh to create it"
        exit 1
    fi
    
    DOCKER_CMD="cd /home/gofr/devroot/${PROJECT_NAME} && source .venv/bin/activate && pytest ${TEST_DIR}/ -v ${COVERAGE_ARGS}"
    docker exec "${CONTAINER_NAME}" bash -c "${DOCKER_CMD}"
    TEST_EXIT_CODE=$?

elif [ "$RUN_UNIT" = true ]; then
    echo -e "${BLUE}Running unit tests only (no servers)...${NC}"
    uv run python -m pytest ${TEST_DIR}/code_quality/ -v ${COVERAGE_ARGS} 2>/dev/null || \
    uv run python -m pytest ${TEST_DIR}/ -v ${COVERAGE_ARGS} -k "not integration"
    TEST_EXIT_CODE=$?

elif [ "$RUN_INTEGRATION" = true ]; then
    echo -e "${BLUE}Running integration tests (with servers)...${NC}"
    uv run python -m pytest ${TEST_DIR}/ -v ${COVERAGE_ARGS}
    TEST_EXIT_CODE=$?

elif [ "$RUN_ALL" = true ]; then
    echo -e "${BLUE}Running ALL tests...${NC}"
    uv run python -m pytest ${TEST_DIR}/ -v ${COVERAGE_ARGS}
    TEST_EXIT_CODE=$?

elif [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
    # Default: run all tests
    uv run python -m pytest ${TEST_DIR}/ -v ${COVERAGE_ARGS}
    TEST_EXIT_CODE=$?
else
    # Custom arguments
    uv run python -m pytest "${PYTEST_ARGS[@]}" ${COVERAGE_ARGS}
    TEST_EXIT_CODE=$?
fi
set -e

# =============================================================================
# CLEANUP
# =============================================================================

if [ "$START_SERVERS" = true ] && [ "$USE_DOCKER" = false ]; then
    echo ""
    echo -e "${YELLOW}Stopping test servers...${NC}"
    stop_servers || true
fi

# Clean up token store
echo -e "${YELLOW}Cleaning up token store...${NC}"
echo "{}" > "${GOFR_DOC_TOKEN_STORE}" 2>/dev/null || true

# =============================================================================
# RESULTS
# =============================================================================

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=== Tests Passed ===${NC}"
    if [ "$COVERAGE" = true ] && [ "$COVERAGE_HTML" = true ]; then
        echo -e "${BLUE}HTML coverage report: ${PROJECT_ROOT}/htmlcov/index.html${NC}"
    fi
else
    echo -e "${RED}=== Tests Failed (exit code: ${TEST_EXIT_CODE}) ===${NC}"
    echo "Server logs:"
    echo "  MCP: ${LOG_DIR}/${PROJECT_NAME}_mcp_test.log"
    echo "  Web: ${LOG_DIR}/${PROJECT_NAME}_web_test.log"
fi

exit $TEST_EXIT_CODE
