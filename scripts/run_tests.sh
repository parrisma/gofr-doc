#!/bin/bash
# =============================================================================
# GOFR-Doc Test Runner
# =============================================================================
# Standardized test runner script for the gofr-doc project.
#
# This script:
# - Sets up virtual environment and PYTHONPATH
# - Starts an ephemeral Vault dev container for auth tests
# - Exports all GOFR_DOC_* env vars needed by conftest.py
# - Runs pytest with optional coverage
# - Cleans up Vault on exit (trap)
#
# Usage:
#   ./scripts/run_tests.sh                          # Run all tests
#   ./scripts/run_tests.sh test/auth/               # Run specific test directory
#   ./scripts/run_tests.sh test/auth/test_authentication.py  # Run single file
#   ./scripts/run_tests.sh -k "token"               # Run tests matching keyword
#   ./scripts/run_tests.sh -v                       # Run with verbose output
#   ./scripts/run_tests.sh --coverage               # Run with coverage report
#   ./scripts/run_tests.sh --coverage-html          # Run with HTML coverage report
#   ./scripts/run_tests.sh --unit                   # Run unit tests only (no servers)
#   ./scripts/run_tests.sh --no-vault               # Skip Vault startup (use existing)
#   ./scripts/run_tests.sh --stop                   # Stop Vault and exit
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

# Source centralized environment configuration
export GOFR_DOC_ENV="TEST"
if [ -f "${SCRIPT_DIR}/gofr-doc.env" ]; then
    source "${SCRIPT_DIR}/gofr-doc.env"
fi

# Load centralized port config (single source of truth)
PORTS_ENV="${PROJECT_ROOT}/lib/gofr-common/config/gofr_ports.env"
if [ -f "${PORTS_ENV}" ]; then
    source "${PORTS_ENV}"
fi

# Set up PYTHONPATH for gofr-common discovery
if [ -d "${PROJECT_ROOT}/lib/gofr-common/src" ]; then
    export PYTHONPATH="${PROJECT_ROOT}:${PROJECT_ROOT}/lib/gofr-common/src:${PYTHONPATH:-}"
elif [ -d "${PROJECT_ROOT}/../gofr-common/src" ]; then
    export PYTHONPATH="${PROJECT_ROOT}:${PROJECT_ROOT}/../gofr-common/src:${PYTHONPATH:-}"
else
    export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
fi

# Test configuration — auth secrets (JWT secret is shared across ALL gofr services)
export GOFR_JWT_SECRET="test-secret-key-for-secure-testing-do-not-use-in-production"
export GOFR_DOC_AUTH_BACKEND="vault"

# Save original container-internal (prod) ports before overwriting with test ports.
# Docker containers listen on these prod ports; port mapping only applies on host.
_GOFR_DOC_MCP_PORT_INTERNAL="${GOFR_DOC_MCP_PORT}"
_GOFR_DOC_MCPO_PORT_INTERNAL="${GOFR_DOC_MCPO_PORT}"
_GOFR_DOC_WEB_PORT_INTERNAL="${GOFR_DOC_WEB_PORT}"

# Docker vs localhost addressing — set after argument parsing (see apply_docker_mode below)
# Defaults are overridden by --docker / --no-docker flags
export GOFR_DOC_HOST="${GOFR_DOC_HOST:-localhost}"
export GOFR_DOC_MCP_PORT="${GOFR_DOC_MCP_PORT_TEST:-8140}"
export GOFR_DOC_MCPO_PORT="${GOFR_DOC_MCPO_PORT_TEST:-8141}"
export GOFR_DOC_WEB_PORT="${GOFR_DOC_WEB_PORT_TEST:-8142}"

# Default: Docker mode (tests run inside dev container on shared network)
USE_DOCKER=true

# Ensure directories exist
mkdir -p "${LOG_DIR}"
mkdir -p "${GOFR_DOC_STORAGE:-${PROJECT_ROOT}/data/storage}"
mkdir -p "${GOFR_DOC_TEMPLATES:-${PROJECT_ROOT}/data/templates}"
mkdir -p "${GOFR_DOC_FRAGMENTS:-${PROJECT_ROOT}/data/fragments}"

# Vault test container configuration
VAULT_CONTAINER_NAME="gofr-vault-test"
VAULT_IMAGE="hashicorp/vault:1.15.4"
VAULT_INTERNAL_PORT=8200
VAULT_TEST_PORT="${GOFR_VAULT_PORT_TEST:-8301}"
VAULT_TEST_TOKEN="${GOFR_TEST_VAULT_DEV_TOKEN:-gofr-dev-root-token}"
TEST_NETWORK="${GOFR_TEST_NETWORK:-gofr-test-net}"
DEV_CONTAINER_NAMES=("gofr-doc-dev")

# Compose-based test services
START_DEV_SCRIPT="${SCRIPT_DIR}/start-test-env.sh"
START_SERVERS=true

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

print_header() {
    echo -e "${GREEN}=== ${PROJECT_NAME} Test Runner ===${NC}"
    echo "Project root: ${PROJECT_ROOT}"
    echo "Environment:  ${GOFR_DOC_ENV}"
    echo "Auth Backend: ${GOFR_DOC_AUTH_BACKEND}"
    echo "Vault URL:    ${GOFR_DOC_VAULT_URL:-not set yet}"
    if [ "$USE_DOCKER" = true ]; then
        echo "Addressing:   Docker hostnames (container network)"
    else
        echo "Addressing:   localhost (published ports)"
    fi
    echo "MCP Host:     ${GOFR_DOC_MCP_HOST}"
    echo "MCP Port:     ${GOFR_DOC_MCP_PORT}"
    echo "Web Host:     ${GOFR_DOC_WEB_HOST}"
    echo "Web Port:     ${GOFR_DOC_WEB_PORT}"
    echo ""
}

is_running_in_docker() {
    [ -f "/.dockerenv" ] && return 0
    grep -qa "docker\|containerd" /proc/1/cgroup 2>/dev/null && return 0
    return 1
}

start_vault_test_container() {
    echo -e "${BLUE}Starting Vault in ephemeral dev mode...${NC}"

    # Ensure test network exists
    if ! docker network ls --format '{{.Name}}' | grep -q "^${TEST_NETWORK}$"; then
        echo "Creating test network: ${TEST_NETWORK}"
        docker network create "${TEST_NETWORK}"
    fi

    # Connect dev container(s) to test network
    for dev_name in "${DEV_CONTAINER_NAMES[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${dev_name}$"; then
            if ! docker network inspect "${TEST_NETWORK}" --format '{{range .Containers}}{{.Name}} {{end}}' | grep -q "${dev_name}"; then
                echo "Connecting ${dev_name} to ${TEST_NETWORK}..."
                docker network connect "${TEST_NETWORK}" "${dev_name}" 2>/dev/null || true
            fi
        fi
    done

    # Pull image if needed
    if ! docker images "${VAULT_IMAGE}" --format '{{.Repository}}' | grep -q "vault"; then
        echo -e "${YELLOW}Pulling Vault image: ${VAULT_IMAGE}${NC}"
        docker pull "${VAULT_IMAGE}"
    fi

    # Remove existing container if any
    if docker ps -aq -f name="^${VAULT_CONTAINER_NAME}$" | grep -q .; then
        echo "Removing existing Vault test container..."
        docker rm -f "${VAULT_CONTAINER_NAME}" 2>/dev/null || true
    fi

    echo "Starting ${VAULT_CONTAINER_NAME} (dev mode, port ${VAULT_TEST_PORT}->${VAULT_INTERNAL_PORT})..."
    docker run -d \
        --name "${VAULT_CONTAINER_NAME}" \
        --hostname "${VAULT_CONTAINER_NAME}" \
        --network "${TEST_NETWORK}" \
        --cap-add IPC_LOCK \
        -p "${VAULT_TEST_PORT}:${VAULT_INTERNAL_PORT}" \
        -e "VAULT_DEV_ROOT_TOKEN_ID=${VAULT_TEST_TOKEN}" \
        -e "VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:${VAULT_INTERNAL_PORT}" \
        -e "VAULT_LOG_LEVEL=warn" \
        "${VAULT_IMAGE}" \
        server -dev > /dev/null

    # Wait for Vault to be ready
    echo -n "Waiting for Vault to be ready"
    local retries=0
    local max_retries=30
    while [ $retries -lt $max_retries ]; do
        if docker exec -e VAULT_ADDR="http://127.0.0.1:${VAULT_INTERNAL_PORT}" \
            "${VAULT_CONTAINER_NAME}" vault status > /dev/null 2>&1; then
            echo " ready!"
            break
        fi
        echo -n "."
        sleep 1
        retries=$((retries + 1))
    done
    if [ $retries -eq $max_retries ]; then
        echo ""
        echo -e "${RED}Vault failed to start within ${max_retries}s${NC}"
        docker logs "${VAULT_CONTAINER_NAME}" 2>&1 | tail -20
        return 1
    fi

    # Enable KV v2 secrets engine
    docker exec -e VAULT_ADDR="http://127.0.0.1:${VAULT_INTERNAL_PORT}" \
        -e VAULT_TOKEN="${VAULT_TEST_TOKEN}" \
        "${VAULT_CONTAINER_NAME}" \
        vault secrets enable -path=secret -version=2 kv 2>/dev/null || true

    # Set Vault URL based on whether we're inside Docker or on the host
    if is_running_in_docker; then
        export GOFR_DOC_VAULT_URL="http://${VAULT_CONTAINER_NAME}:${VAULT_INTERNAL_PORT}"
    else
        export GOFR_DOC_VAULT_URL="http://localhost:${VAULT_TEST_PORT}"
    fi
    export GOFR_DOC_VAULT_TOKEN="${VAULT_TEST_TOKEN}"

    echo -e "${GREEN}Vault started successfully${NC}"
    echo "  Container: ${VAULT_CONTAINER_NAME}"
    echo "  Network:   ${TEST_NETWORK}"
    echo "  URL:       ${GOFR_DOC_VAULT_URL}"
    echo "  Token:     ${GOFR_DOC_VAULT_TOKEN}"
    echo ""
}

stop_vault_test_container() {
    echo -e "${YELLOW}Stopping Vault test container...${NC}"
    if docker ps -q -f name="^${VAULT_CONTAINER_NAME}$" | grep -q .; then
        docker stop "${VAULT_CONTAINER_NAME}" 2>/dev/null || true
        docker rm "${VAULT_CONTAINER_NAME}" 2>/dev/null || true
        echo -e "${GREEN}Vault container stopped${NC}"
    else
        echo "Vault container was not running"
    fi

    for dev_name in "${DEV_CONTAINER_NAMES[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${dev_name}$"; then
            docker network disconnect "${TEST_NETWORK}" "${dev_name}" 2>/dev/null || true
        fi
    done
}

cleanup_environment() {
    echo -e "${YELLOW}Cleaning up test environment...${NC}"
    stop_services
    stop_vault_test_container
    rm -f data/sessions/*.json 2>/dev/null || true
    echo -e "${GREEN}Cleanup complete${NC}"
}

# ─── Docker Compose Service Management ───────────────────────────────────────

start_services() {
    echo -e "${GREEN}=== Starting Ephemeral Docker Services ===${NC}"
    if [ ! -x "${START_DEV_SCRIPT}" ]; then
        echo -e "${RED}start-test-env.sh not found or not executable: ${START_DEV_SCRIPT}${NC}"
        exit 1
    fi
    "${START_DEV_SCRIPT}" --build
    echo ""
}

stop_services() {
    echo -e "${YELLOW}Stopping ephemeral Docker services...${NC}"
    if [ -x "${START_DEV_SCRIPT}" ]; then
        "${START_DEV_SCRIPT}" --down 2>/dev/null || true
    fi
    echo -e "${GREEN}Services stopped${NC}"
}

# =============================================================================
# ARGUMENT PARSING
# =============================================================================

COVERAGE=false
COVERAGE_HTML=false
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_ALL=false
STOP_ONLY=false
CLEANUP_ONLY=false
SKIP_VAULT=false
PYTEST_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
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
            shift
            ;;
        --integration)
            RUN_INTEGRATION=true
            shift
            ;;
        --all)
            RUN_ALL=true
            shift
            ;;
        --no-vault)
            SKIP_VAULT=true
            shift
            ;;
        --no-servers)
            START_SERVERS=false
            shift
            ;;
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --no-docker)
            USE_DOCKER=false
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
            echo "  --coverage       Run with coverage report"
            echo "  --coverage-html  Run with HTML coverage report"
            echo "  --unit           Run unit tests only"
            echo "  --integration    Run integration tests"
            echo "  --all            Run all test categories"
            echo "  --no-vault       Skip Vault startup (use running instance)"
            echo "  --no-servers     Skip Docker Compose service startup"
            echo "  --docker         Use Docker hostnames for integration tests (default)"
            echo "  --no-docker      Use localhost+published ports for integration tests"
            echo "  --stop           Stop services + Vault and exit"
            echo "  --cleanup-only   Clean environment and exit"
            echo "  --help, -h       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 test/auth/                       # Run auth tests"
            echo "  $0 test/auth/test_authentication.py # Run single file"
            echo "  $0 -k 'token'                       # Run tests matching keyword"
            echo "  $0 -v test/web/                     # Verbose web tests"
            exit 0
            ;;
        *)
            PYTEST_ARGS+=("$1")
            shift
            ;;
    esac
done

# =============================================================================
# APPLY DOCKER / LOCALHOST ADDRESSING MODE
# =============================================================================

if [ "$USE_DOCKER" = true ]; then
    # Docker mode: use container hostnames + internal (prod) ports.
    # The dev container and test containers share gofr-test-net.
    # Containers listen on prod ports internally (8040/8041/8042);
    # port mapping (e.g. 8140→8040) only applies to host access.
    export GOFR_DOC_MCP_HOST="gofr-doc-mcp-test"
    export GOFR_DOC_WEB_HOST="gofr-doc-web-test"
    export GOFR_DOC_IMAGE_SERVER_HOST="gofr-doc-dev"
    export GOFR_DOC_MCP_PORT="${_GOFR_DOC_MCP_PORT_INTERNAL}"
    export GOFR_DOC_MCPO_PORT="${_GOFR_DOC_MCPO_PORT_INTERNAL}"
    export GOFR_DOC_WEB_PORT="${_GOFR_DOC_WEB_PORT_INTERNAL}"
else
    # Localhost mode: use published test ports (prod + 100).
    export GOFR_DOC_MCP_HOST="localhost"
    export GOFR_DOC_WEB_HOST="localhost"
    export GOFR_DOC_IMAGE_SERVER_HOST="localhost"
    export GOFR_DOC_MCP_PORT="${GOFR_DOC_MCP_PORT_TEST}"
    export GOFR_DOC_MCPO_PORT="${GOFR_DOC_MCPO_PORT_TEST}"
    export GOFR_DOC_WEB_PORT="${GOFR_DOC_WEB_PORT_TEST}"
fi

# =============================================================================
# MAIN EXECUTION
# =============================================================================

# Handle stop-only mode
if [ "$STOP_ONLY" = true ]; then
    echo -e "${YELLOW}Stopping services and Vault...${NC}"
    stop_services
    stop_vault_test_container
    exit 0
fi

# Handle cleanup-only mode
if [ "$CLEANUP_ONLY" = true ]; then
    cleanup_environment
    exit 0
fi

# Start Vault (unless --no-vault or --unit)
if [ "$SKIP_VAULT" = false ] && [ "$RUN_UNIT" = false ]; then
    start_vault_test_container
    trap 'stop_services; stop_vault_test_container' EXIT
else
    # If skipping Vault, ensure env vars are set for an existing instance
    if [ -z "${GOFR_DOC_VAULT_URL:-}" ]; then
        if is_running_in_docker; then
            export GOFR_DOC_VAULT_URL="http://${VAULT_CONTAINER_NAME}:${VAULT_INTERNAL_PORT}"
        else
            export GOFR_DOC_VAULT_URL="http://localhost:${VAULT_TEST_PORT}"
        fi
    fi
    export GOFR_DOC_VAULT_TOKEN="${GOFR_DOC_VAULT_TOKEN:-${VAULT_TEST_TOKEN}}"
    trap 'stop_services' EXIT
fi

# Start test services via Docker Compose (unless --unit)
if [ "$RUN_UNIT" = false ] && [ "$START_SERVERS" = true ]; then
    start_services
fi

print_header

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

if [ "$RUN_UNIT" = true ]; then
    echo -e "${BLUE}Running unit tests only...${NC}"
    uv run python -m pytest ${TEST_DIR}/ -v ${COVERAGE_ARGS} -k "not integration"
    TEST_EXIT_CODE=$?

elif [ "$RUN_INTEGRATION" = true ]; then
    echo -e "${BLUE}Running integration tests...${NC}"
    uv run python -m pytest ${TEST_DIR}/ -v ${COVERAGE_ARGS} -k "integration"
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
    # Custom arguments (targeted tests, -k filters, etc.)
    uv run python -m pytest "${PYTEST_ARGS[@]}" -v ${COVERAGE_ARGS}
    TEST_EXIT_CODE=$?
fi
set -e

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
fi

exit $TEST_EXIT_CODE
