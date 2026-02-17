#!/bin/bash
# =============================================================================
# gofr-doc Test Environment Manager
# =============================================================================
# Mirrors the gofr-dig start-test-env.sh pattern.
#
# Builds the prod image (if needed), creates the test network, and starts
# the compose.dev.yml stack.  Polls Docker health checks until all services
# are healthy or a timeout is reached.
#
# Usage:
#   ./scripts/start-test-env.sh            # Start (build if image missing)
#   ./scripts/start-test-env.sh --build    # Force rebuild + start
#   ./scripts/start-test-env.sh --down     # Tear down the stack
# =============================================================================

set -euo pipefail

# ── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

COMPOSE_FILE="${PROJECT_ROOT}/docker/compose.dev.yml"
DOCKERFILE="${PROJECT_ROOT}/docker/Dockerfile.prod"
PORTS_ENV="${PROJECT_ROOT}/lib/gofr-common/config/gofr_ports.env"

# ── Colours ──────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ── Helpers ──────────────────────────────────────────────────────────────────

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*" >&2; exit 1; }

# ── Ports (from single source of truth) ──────────────────────────────────────

if [ ! -f "${PORTS_ENV}" ]; then
    fail "Port config not found: ${PORTS_ENV}"
fi
set -a
source "${PORTS_ENV}"
set +a

# Host port defaults (test ports = prod + 100)
export GOFR_DOC_MCP_HOST_PORT=${GOFR_DOC_MCP_PORT_TEST}
export GOFR_DOC_MCPO_HOST_PORT=${GOFR_DOC_MCPO_PORT_TEST}
export GOFR_DOC_WEB_HOST_PORT=${GOFR_DOC_WEB_PORT_TEST}

ok "Ports loaded — test ports (MCP=${GOFR_DOC_MCP_HOST_PORT}, MCPO=${GOFR_DOC_MCPO_HOST_PORT}, Web=${GOFR_DOC_WEB_HOST_PORT})"

MCP_TEST=${GOFR_DOC_MCP_PORT_TEST:-8140}
MCPO_TEST=${GOFR_DOC_MCPO_PORT_TEST:-8141}
WEB_TEST=${GOFR_DOC_WEB_PORT_TEST:-8142}

IMAGE_NAME="gofr-doc-prod:latest"
TEST_NETWORK="gofr-test-net"

CONTAINERS=("gofr-doc-mcp-test" "gofr-doc-mcpo-test" "gofr-doc-web-test")

# ── Prerequisites ────────────────────────────────────────────────────────────

echo ""
info "Checking prerequisites..."

if ! command -v docker &>/dev/null; then
    fail "docker is not installed or not on PATH"
fi

if ! docker info &>/dev/null 2>&1; then
    fail "Docker daemon is not running (or current user cannot connect)"
fi

if ! docker compose version &>/dev/null 2>&1; then
    fail "docker compose plugin is not installed (need 'docker compose', not 'docker-compose')"
fi

ok "Docker + Compose available"

# ── Argument parsing ────────────────────────────────────────────────────────

FORCE_BUILD=false
TEAR_DOWN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --build)  FORCE_BUILD=true; shift ;;
        --down)   TEAR_DOWN=true;   shift ;;
        --help|-h)
            echo "Usage: $0 [--build] [--down] [--help]"
            echo ""
            echo "  --build   Force rebuild before starting"
            echo "  --down    Stop and remove all test services"
            echo "  --help    Show this help message"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Helper: tear down ───────────────────────────────────────────────────────

tear_down() {
    info "Tearing down gofr-doc test stack..."
    docker compose -f "${COMPOSE_FILE}" --project-directory "${PROJECT_ROOT}" down --remove-orphans 2>/dev/null || true

    # Compose should remove these, but container_name is fixed in compose.dev.yml,
    # and stale containers can survive interrupted runs.
    docker rm -f \
        gofr-vault-test \
        gofr-vault-init-test \
        gofr-doc-mcp-test \
        gofr-doc-mcpo-test \
        gofr-doc-web-test \
        2>/dev/null || true
    ok "Stack removed."
}

if [ "$TEAR_DOWN" = true ]; then
    tear_down
    exit 0
fi

# ── Ensure test network ─────────────────────────────────────────────────────

if ! docker network ls --format '{{.Name}}' | grep -q "^${TEST_NETWORK}$"; then
    info "Creating test network: ${TEST_NETWORK}"
    docker network create "${TEST_NETWORK}"
else
    ok "Network '${TEST_NETWORK}' exists"
fi

# ── Build image (if missing or --build) ──────────────────────────────────────

VERSION=$(grep -m1 '^version = ' "${PROJECT_ROOT}/pyproject.toml" | sed 's/version = "\(.*\)"/\1/')

if [ "$FORCE_BUILD" = true ] || ! docker image inspect "${IMAGE_NAME}" &>/dev/null; then
    if [ "$FORCE_BUILD" = true ]; then
        info "Force-building image..."
    else
        info "Image '${IMAGE_NAME}' not found — building automatically..."
    fi
    docker build \
        -f "${DOCKERFILE}" \
        -t "gofr-doc-prod:${VERSION}" \
        -t "${IMAGE_NAME}" \
        "${PROJECT_ROOT}"
    ok "Built gofr-doc-prod:${VERSION} (also tagged :latest)"
else
    ok "Image '${IMAGE_NAME}' already exists (use --build to rebuild)"
fi

# ── Remove stale containers ─────────────────────────────────────────────────

tear_down

# ── Start the stack ──────────────────────────────────────────────────────────

info "Starting gofr-doc test stack..."
set +e
docker compose -f "${COMPOSE_FILE}" --project-directory "${PROJECT_ROOT}" up -d
COMPOSE_UP_EXIT_CODE=$?
set -e

if [ ${COMPOSE_UP_EXIT_CODE} -ne 0 ]; then
    echo -e "${RED}=== docker compose up failed (exit code: ${COMPOSE_UP_EXIT_CODE}) ===${NC}"
    echo ""
    echo "--- docker compose ps ---"
    docker compose -f "${COMPOSE_FILE}" --project-directory "${PROJECT_ROOT}" ps 2>&1 || true
    echo ""

    echo "--- vault logs (gofr-vault-test) ---"
    docker logs gofr-vault-test 2>&1 || true
    echo ""
    echo "--- vault-init logs (gofr-vault-init-test) ---"
    docker logs gofr-vault-init-test 2>&1 || true
    echo ""

    for cname in "${CONTAINERS[@]}"; do
        echo "--- container logs (${cname}) ---"
        docker logs "${cname}" 2>&1 || true
        echo ""

        echo "--- health status (${cname}) ---"
        docker inspect --format='{{json .State.Health}}' "${cname}" 2>&1 || true
        echo ""
    done

    exit ${COMPOSE_UP_EXIT_CODE}
fi

# ── Poll health checks ────────────────────────────────────────────────────────

MAX_RETRIES=20
RETRY_INTERVAL=3

info "Waiting for services to become healthy (max $((MAX_RETRIES * RETRY_INTERVAL))s)..."

all_healthy=false
for attempt in $(seq 1 ${MAX_RETRIES}); do
    healthy_count=0
    for cname in "${CONTAINERS[@]}"; do
        status=$(docker inspect --format='{{.State.Health.Status}}' "${cname}" 2>/dev/null || echo "missing")
        if [ "${status}" = "healthy" ]; then
            healthy_count=$((healthy_count + 1))
        fi
    done

    if [ ${healthy_count} -eq ${#CONTAINERS[@]} ]; then
        all_healthy=true
        break
    fi

    echo -n "  [${attempt}/${MAX_RETRIES}] healthy: ${healthy_count}/${#CONTAINERS[@]}"
    for cname in "${CONTAINERS[@]}"; do
        status=$(docker inspect --format='{{.State.Health.Status}}' "${cname}" 2>/dev/null || echo "?")
        echo -n "  ${cname##gofr-doc-}=${status}"
    done
    echo ""
    sleep "${RETRY_INTERVAL}"
done

# ── Report ───────────────────────────────────────────────────────────────────

echo ""
if [ "$all_healthy" = true ]; then
    ok "All gofr-doc test services healthy"
else
    echo -e "${RED}=== Some services did NOT become healthy ===${NC}"
    for cname in "${CONTAINERS[@]}"; do
        status=$(docker inspect --format='{{.State.Health.Status}}' "${cname}" 2>/dev/null || echo "missing")
        case "$status" in
            *healthy*) ok "${cname##gofr-doc-}: ${status}" ;;
            *)         warn "${cname##gofr-doc-}: ${status}" ;;
        esac
        if [ "${status}" != "healthy" ]; then
            echo "  --- full logs ---"
            docker logs "${cname}" 2>&1
        fi
    done
    exit 1
fi

echo ""
echo "======================================================================="
echo "  gofr-doc test stack is running"
echo "======================================================================="
echo ""
echo "  MCP Server:  http://localhost:${MCP_TEST}/mcp"
echo "  MCPO Server: http://localhost:${MCPO_TEST}/openapi.json"
echo "  Web Server:  http://localhost:${WEB_TEST}/ping"
echo ""
echo "  Network:     ${TEST_NETWORK}"
echo "  Auth:        ENABLED (JWT + Vault)"
echo ""
echo "  Logs:    docker compose -f ${COMPOSE_FILE} logs -f"
echo "  Status:  docker compose -f ${COMPOSE_FILE} ps"
echo "  Stop:    $0 --down"
echo "  Rebuild: $0 --build"
echo ""
