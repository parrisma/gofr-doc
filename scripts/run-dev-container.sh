#!/bin/bash
# Run GOFR-DOC development container
# Canonical location for the developer workflow entrypoint.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

GOFR_USER="gofr"
GOFR_UID=1000
GOFR_GID=1000

CONTAINER_NAME="gofr-doc-dev"
IMAGE_NAME="gofr-doc-dev:latest"

MCP_PORT="${GOFRDOC_MCP_PORT:-9040}"
MCPO_PORT="${GOFRDOC_MCPO_PORT:-9041}"
WEB_PORT="${GOFRDOC_WEB_PORT:-9042}"
DOCKER_NETWORK="${GOFRDOC_DOCKER_NETWORK:-gofr-net}"

while [ $# -gt 0 ]; do
    case $1 in
        --mcp-port)
            MCP_PORT="$2"; shift 2 ;;
        --mcpo-port)
            MCPO_PORT="$2"; shift 2 ;;
        --web-port)
            WEB_PORT="$2"; shift 2 ;;
        --network)
            DOCKER_NETWORK="$2"; shift 2 ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--mcp-port PORT] [--mcpo-port PORT] [--web-port PORT] [--network NAME]"
            exit 1
            ;;
    esac
done

echo "======================================================================="
echo "Starting GOFR-DOC Development Container"
echo "======================================================================="
echo "User: ${GOFR_USER} (UID=${GOFR_UID}, GID=${GOFR_GID})"
echo "Ports: MCP=$MCP_PORT, MCPO=$MCPO_PORT, Web=$WEB_PORT"
echo "Network: $DOCKER_NETWORK"
echo "======================================================================="

if ! docker network inspect $DOCKER_NETWORK >/dev/null 2>&1; then
    echo "Creating network: $DOCKER_NETWORK"
    docker network create $DOCKER_NETWORK
fi

VOLUME_NAME="gofr-doc-data-dev"
if ! docker volume inspect $VOLUME_NAME >/dev/null 2>&1; then
    echo "Creating volume: $VOLUME_NAME"
    docker volume create $VOLUME_NAME
fi

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping existing container: $CONTAINER_NAME"
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

DOCKER_SOCK="/var/run/docker.sock"
DOCKER_GID_ARGS=""
if [ -S "$DOCKER_SOCK" ]; then
    DOCKER_SOCK_GID=$(stat -c '%g' "$DOCKER_SOCK")
    echo "Docker socket GID: $DOCKER_SOCK_GID"
    DOCKER_GID_ARGS="--group-add $DOCKER_SOCK_GID"
fi

docker run -d \
    --name "$CONTAINER_NAME" \
    --network "$DOCKER_NETWORK" \
    $DOCKER_GID_ARGS \
    -p ${MCP_PORT}:8040 \
    -p ${MCPO_PORT}:8041 \
    -p ${WEB_PORT}:8042 \
    -v "$PROJECT_ROOT:/home/gofr/devroot/gofr-doc:rw" \
    -v "$PROJECT_ROOT/../gofr-dig:/home/gofr/devroot/gofr-dig:ro" \
    -v "$PROJECT_ROOT/../gofr-plot:/home/gofr/devroot/gofr-plot:ro" \
    -v "$PROJECT_ROOT/../gofr-iq:/home/gofr/devroot/gofr-iq:ro" \
    -v ${VOLUME_NAME}:/home/gofr/devroot/gofr-doc/data:rw \
    -v gofr-secrets:/run/gofr-secrets:ro \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -e GOFRDOC_ENV=development \
    -e GOFRDOC_DEBUG=true \
    -e GOFRDOC_LOG_LEVEL=DEBUG \
    -e GOFR_DOC_AUTH_BACKEND=vault \
    -e GOFR_DOC_VAULT_URL=http://gofr-vault:8201 \
    -e GOFR_DOC_VAULT_PATH_PREFIX=gofr/auth \
    -e GOFR_DOC_VAULT_MOUNT=secret \
    "$IMAGE_NAME"

TEST_NETWORK="${GOFR_TEST_NETWORK:-gofr-test-net}"
if ! docker network inspect "$TEST_NETWORK" >/dev/null 2>&1; then
    echo "Creating test network: $TEST_NETWORK"
    docker network create "$TEST_NETWORK"
fi

echo "Connecting $CONTAINER_NAME to $TEST_NETWORK..."
docker network connect "$TEST_NETWORK" "$CONTAINER_NAME" 2>/dev/null || true

echo ""
echo "======================================================================="
echo "Container started: $CONTAINER_NAME"
echo "======================================================================="
echo "Networks: $DOCKER_NETWORK, $TEST_NETWORK"
