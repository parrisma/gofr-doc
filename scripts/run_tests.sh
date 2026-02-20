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
if [ -f "${SCRIPT_DIR}/project.env" ]; then
    source "${SCRIPT_DIR}/project.env"
fi

# Load centralized port config (single source of truth)
PORTS_ENV="${PROJECT_ROOT}/lib/gofr-common/config/gofr_ports.env"
if [ -f "${PORTS_ENV}" ]; then
    source "${PORTS_ENV}"
fi

# Test ports come from gofr_ports.env (sourced above) -- no hardcoded fallbacks
: "${GOFR_DOC_MCP_PORT_TEST:?GOFR_DOC_MCP_PORT_TEST not set -- source gofr_ports.env}"
: "${GOFR_DOC_MCPO_PORT_TEST:?GOFR_DOC_MCPO_PORT_TEST not set -- source gofr_ports.env}"
: "${GOFR_DOC_WEB_PORT_TEST:?GOFR_DOC_WEB_PORT_TEST not set -- source gofr_ports.env}"

# Set up PYTHONPATH for gofr-common discovery
if [ -d "${PROJECT_ROOT}/lib/gofr-common/src" ]; then
    export PYTHONPATH="${PROJECT_ROOT}:${PROJECT_ROOT}/lib/gofr-common/src:${PYTHONPATH:-}"
elif [ -d "${PROJECT_ROOT}/../gofr-common/src" ]; then
    export PYTHONPATH="${PROJECT_ROOT}:${PROJECT_ROOT}/../gofr-common/src:${PYTHONPATH:-}"
else
    export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
fi

# Test configuration -- auth (JWT signing secret is seeded into Vault by compose)
export GOFR_DOC_AUTH_BACKEND="vault"

# Save original container-internal (prod) ports before overwriting with test ports.
# Docker containers listen on these prod ports; port mapping only applies on host.
_GOFR_DOC_MCP_PORT_INTERNAL="${GOFR_DOC_MCP_PORT}"
_GOFR_DOC_MCPO_PORT_INTERNAL="${GOFR_DOC_MCPO_PORT}"
_GOFR_DOC_WEB_PORT_INTERNAL="${GOFR_DOC_WEB_PORT}"

# Docker vs localhost addressing — set after argument parsing (see apply_docker_mode below)
# Defaults are overridden by --docker / --no-docker flags
export GOFR_DOC_HOST="${GOFR_DOC_HOST:-localhost}"
export GOFR_DOC_MCP_PORT="${GOFR_DOC_MCP_PORT_TEST}"
export GOFR_DOC_MCPO_PORT="${GOFR_DOC_MCPO_PORT_TEST}"
export GOFR_DOC_WEB_PORT="${GOFR_DOC_WEB_PORT_TEST}"

# Default: Docker mode (tests run inside dev container on shared network)
USE_DOCKER=true

# Ensure directories exist
mkdir -p "${LOG_DIR}"
mkdir -p "${GOFR_DOC_STORAGE:-${PROJECT_ROOT}/data/storage}"
mkdir -p "${GOFR_DOC_TEMPLATES:-${PROJECT_ROOT}/data/templates}"
mkdir -p "${GOFR_DOC_FRAGMENTS:-${PROJECT_ROOT}/data/fragments}"

# Vault test container configuration (managed by compose.dev.yml)
VAULT_CONTAINER_NAME="gofr-doc-vault-test"
VAULT_INTERNAL_PORT=8200
VAULT_TEST_PORT="${GOFR_VAULT_PORT_TEST:?GOFR_VAULT_PORT_TEST not set -- source gofr_ports.env}"
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
    echo "MCP URL:      ${GOFR_DOC_MCP_URL:-not set yet}"
    echo "MCPO URL:     ${GOFR_DOC_MCPO_URL:-not set yet}"
    echo "Web URL:      ${GOFR_DOC_WEB_URL:-not set yet}"
    echo ""
}

is_running_in_docker() {
    [ -f "/.dockerenv" ] && return 0
    grep -qa "docker\|containerd" /proc/1/cgroup 2>/dev/null && return 0
    return 1
}

start_vault_test_container() {
    echo -e "${BLUE}Ensuring test network and dev container connectivity...${NC}"

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

    # Vault is started by compose.dev.yml; set env vars for pytest (runs in dev container)
    if is_running_in_docker; then
        export GOFR_DOC_VAULT_URL="http://${VAULT_CONTAINER_NAME}:${VAULT_INTERNAL_PORT}"
    else
        export GOFR_DOC_VAULT_URL="http://127.0.0.1:${VAULT_TEST_PORT}"
    fi
    export GOFR_DOC_VAULT_TOKEN="${VAULT_TEST_TOKEN}"

    # gofr-common tests use the generic GOFR_VAULT_* env vars
    export GOFR_VAULT_URL="${GOFR_DOC_VAULT_URL}"
    export GOFR_VAULT_TOKEN="${GOFR_DOC_VAULT_TOKEN}"

    echo -e "${GREEN}Vault env vars set for pytest${NC}"
    echo "  URL:   ${GOFR_DOC_VAULT_URL}"
    echo "  Token: ${GOFR_DOC_VAULT_TOKEN}"
    echo ""
}

stop_vault_test_container() {
    # Vault is managed by compose.dev.yml -- nothing to do here
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

run_code_quality_gate() {
    echo -e "${BLUE}Running code quality gate...${NC}"
    set +e
    uv run python -m pytest ${TEST_DIR}/test_code_quality.py -v
    local gate_exit_code=$?
    set -e

    if [ $gate_exit_code -ne 0 ]; then
        echo -e "${RED}ALL Code quality issues must be solved before running other tests${NC}"
        exit $gate_exit_code
    fi
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
        --no-servers|--without-servers)
            START_SERVERS=false
            shift
            ;;
        --with-servers|--start-servers)
            START_SERVERS=true
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
            echo "  --integration    Run integration tests"
            echo "  --all            Run all test categories"
            echo "  --no-vault       Skip Vault startup (use running instance)"
            echo "  --no-servers     Don't start Docker services"
            echo "  --with-servers   Start Docker services (default)"
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

    # Full URLs for integration tests (container hostname + internal prod port)
    export GOFR_DOC_MCP_URL="http://gofr-doc-mcp-test:${_GOFR_DOC_MCP_PORT_INTERNAL}/mcp"
    export GOFR_DOC_MCPO_URL="http://gofr-doc-mcpo-test:${_GOFR_DOC_MCPO_PORT_INTERNAL}"
    export GOFR_DOC_WEB_URL="http://gofr-doc-web-test:${_GOFR_DOC_WEB_PORT_INTERNAL}"
else
    # Localhost mode: use published test ports (prod + 100).
    export GOFR_DOC_MCP_HOST="localhost"
    export GOFR_DOC_WEB_HOST="localhost"
    export GOFR_DOC_IMAGE_SERVER_HOST="localhost"
    export GOFR_DOC_MCP_PORT="${GOFR_DOC_MCP_PORT_TEST}"
    export GOFR_DOC_MCPO_PORT="${GOFR_DOC_MCPO_PORT_TEST}"
    export GOFR_DOC_WEB_PORT="${GOFR_DOC_WEB_PORT_TEST}"

    export GOFR_DOC_MCP_URL="http://localhost:${GOFR_DOC_MCP_PORT}/mcp"
    export GOFR_DOC_MCPO_URL="http://localhost:${GOFR_DOC_MCPO_PORT}"
    export GOFR_DOC_WEB_URL="http://localhost:${GOFR_DOC_WEB_PORT}"
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

# Fail-fast quality gate before starting services and running other tests
run_code_quality_gate

# Set up network and Vault env vars (unless --no-vault)
if [ "$SKIP_VAULT" = false ]; then
    start_vault_test_container
    trap 'stop_services; stop_vault_test_container' EXIT
else
    # If skipping Vault setup, ensure env vars are set for an existing instance
    if [ -z "${GOFR_DOC_VAULT_URL:-}" ]; then
        if is_running_in_docker; then
            export GOFR_DOC_VAULT_URL="http://${VAULT_CONTAINER_NAME}:${VAULT_INTERNAL_PORT}"
        else
            export GOFR_DOC_VAULT_URL="http://127.0.0.1:${VAULT_TEST_PORT}"
        fi
    fi
    export GOFR_DOC_VAULT_TOKEN="${GOFR_DOC_VAULT_TOKEN:-${VAULT_TEST_TOKEN}}"

    export GOFR_VAULT_URL="${GOFR_VAULT_URL:-${GOFR_DOC_VAULT_URL}}"
    export GOFR_VAULT_TOKEN="${GOFR_VAULT_TOKEN:-${GOFR_DOC_VAULT_TOKEN}}"
    trap 'stop_services' EXIT
fi

# Start test services via Docker Compose
if [ "$START_SERVERS" = true ]; then
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

if [ "$RUN_INTEGRATION" = true ]; then
    echo -e "${BLUE}Running integration tests...${NC}"
    uv run python -m pytest ${TEST_DIR}/ ${COVERAGE_ARGS} -k "integration"
    TEST_EXIT_CODE=$?

elif [ "$RUN_ALL" = true ]; then
    echo -e "${BLUE}Running ALL tests...${NC}"
    uv run python -m pytest ${TEST_DIR}/ ${COVERAGE_ARGS}
    TEST_EXIT_CODE=$?

elif [ ${#PYTEST_ARGS[@]} -eq 0 ]; then
    # Default: run all tests
    uv run python -m pytest ${TEST_DIR}/ ${COVERAGE_ARGS}
    TEST_EXIT_CODE=$?
else
    # Custom arguments (targeted tests, -k filters, etc.)
    HAS_POSITIONAL_PATH=false
    for arg in "${PYTEST_ARGS[@]}"; do
        if [[ "${arg}" != -* ]] && [ -e "${arg}" ]; then
            HAS_POSITIONAL_PATH=true
            break
        fi
    done

    if [ "${HAS_POSITIONAL_PATH}" = true ]; then
        uv run python -m pytest "${PYTEST_ARGS[@]}" ${COVERAGE_ARGS}
    else
        uv run python -m pytest ${TEST_DIR}/ "${PYTEST_ARGS[@]}" ${COVERAGE_ARGS}
    fi
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
    echo "Docker service logs:"
    echo "  docker compose -f docker/compose.dev.yml logs"
fi

exit $TEST_EXIT_CODE
