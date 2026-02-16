#!/bin/bash
# =============================================================================
# gofr-doc Production Stack — compose-based launcher
# =============================================================================
# Starts the production stack using docker compose (3 separate containers:
# mcp, mcpo, web) instead of a single supervisor-managed container.
#
# Usage:
#   ./docker/start-prod.sh               # Start stack
#   ./docker/start-prod.sh --build       # Force rebuild image first
#   ./docker/start-prod.sh --down        # Stop and remove all services
#   ./docker/start-prod.sh --no-auth     # Disable JWT authentication
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKER_DIR="$SCRIPT_DIR"

COMPOSE_FILE="$DOCKER_DIR/compose.prod.yml"
IMAGE_NAME="gofr-doc-prod:latest"
NETWORK_NAME="gofr-net"
PORTS_ENV="$PROJECT_ROOT/lib/gofr-common/config/gofr_ports.env"

FORCE_BUILD=false
NO_AUTH=false
DO_DOWN=false

# ---- Parse arguments --------------------------------------------------------
while [ $# -gt 0 ]; do
    case "$1" in
        --build)     FORCE_BUILD=true; shift ;;
        --no-auth)   NO_AUTH=true; shift ;;
        --down)      DO_DOWN=true; shift ;;
        --help|-h)
            sed -n '/^# Usage:/,/^# ====/p' "$0" | head -n -1 | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "=== gofr-doc Production Stack ==="

# ---- Source centralised port config -----------------------------------------
if [ -f "$PORTS_ENV" ]; then
    set -a && source "$PORTS_ENV" && set +a
    echo "Ports loaded from gofr_ports.env"
else
    echo "WARNING: $PORTS_ENV not found, using defaults"
fi

MCP_PORT="${GOFR_DOC_MCP_PORT:-8040}"
MCPO_PORT="${GOFR_DOC_MCPO_PORT:-8041}"
WEB_PORT="${GOFR_DOC_WEB_PORT:-8042}"

# ---- Handle --down ----------------------------------------------------------
if [ "$DO_DOWN" = true ]; then
    echo "Stopping gofr-doc production stack..."
    docker compose -f "$COMPOSE_FILE" down
    echo "Stack stopped."
    exit 0
fi

# ---- Create network if needed -----------------------------------------------
if ! docker network inspect ${NETWORK_NAME} >/dev/null 2>&1; then
    echo "Creating network: ${NETWORK_NAME}"
    docker network create ${NETWORK_NAME}
fi

# ---- Build image if needed --------------------------------------------------
if [ "$FORCE_BUILD" = true ] || ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "Building production image..."
    docker build -f "$DOCKER_DIR/Dockerfile.prod" -t "$IMAGE_NAME" "$PROJECT_ROOT"
fi

# ---- Auth flag ---------------------------------------------------------------
if [ "$NO_AUTH" = true ]; then
    export GOFR_DOC_NO_AUTH=1
    echo "Authentication DISABLED (--no-auth)"
fi

# ---- Start compose stack ----------------------------------------------------
echo ""
echo "Starting compose stack..."
echo "  MCP Port:  ${MCP_PORT}"
echo "  MCPO Port: ${MCPO_PORT}"
echo "  Web Port:  ${WEB_PORT}"
echo ""

docker compose -f "$COMPOSE_FILE" up -d

# ---- Health check -----------------------------------------------------------
echo ""
echo "Waiting for services..."
sleep 5

HEALTHY=true
for svc in mcp mcpo web; do
    CONTAINER="gofr-doc-${svc}"
    if docker ps -q -f name="${CONTAINER}" | grep -q .; then
        echo "  ✓ ${CONTAINER} running"
    else
        echo "  ✗ ${CONTAINER} NOT running"
        HEALTHY=false
    fi
done

echo ""
if [ "$HEALTHY" = true ]; then
    echo "=== Stack Started Successfully ==="
    echo "MCP Server:  http://localhost:${MCP_PORT}/mcp"
    echo "MCPO Server: http://localhost:${MCPO_PORT}"
    echo "Web Server:  http://localhost:${WEB_PORT}"
    echo ""
    echo "Commands:"
    echo "  Logs:   docker compose -f ${COMPOSE_FILE} logs -f"
    echo "  Stop:   ./docker/start-prod.sh --down"
    echo "  Status: docker compose -f ${COMPOSE_FILE} ps"
else
    echo "ERROR: Some services failed to start"
    docker compose -f "$COMPOSE_FILE" logs --tail=20
    exit 1
fi
