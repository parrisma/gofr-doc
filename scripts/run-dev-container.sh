#!/bin/bash
# Run GOFR-DOC development container
# Uses gofr-doc-dev:latest image (built from gofr-base:latest)
# Runs as the host UID/GID so bind-mounted files have correct ownership.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKER_DIR="$PROJECT_ROOT/docker"
# gofr-common is now a git submodule at lib/gofr-common, no separate mount needed

# Detect host user's UID/GID (the dev container must match so bind-mounted
# files have the right ownership).
GOFR_UID=$(id -u)
GOFR_GID=$(id -g)

# Container and image names
CONTAINER_NAME="gofr-doc-dev"
IMAGE_NAME="gofr-doc-dev:latest"

# Ports (gofr-doc exposes MCP/MCPO/Web on 8040-8042 inside the container)
MCP_PORT="${GOFRDOC_MCP_PORT:-9040}"
MCPO_PORT="${GOFRDOC_MCPO_PORT:-9041}"
WEB_PORT="${GOFRDOC_WEB_PORT:-9042}"

# Primary network for dev; also connects to gofr-test-net for tests
DOCKER_NETWORK="${GOFRDOC_DOCKER_NETWORK:-gofr-net}"
TEST_NETWORK="${GOFR_TEST_NETWORK:-gofr-test-net}"

# Host user's home directory (for container mount destination paths).
# Override with --host-home when the default doesn't match.
HOST_HOME="${HOST_HOME:-}"

usage() {
        cat <<EOF
Usage: $0 [OPTIONS]

Options:
    --mcp-port PORT      Host port to map to container MCP (default: $MCP_PORT)
    --mcpo-port PORT     Host port to map to container MCPO (default: $MCPO_PORT)
    --web-port PORT      Host port to map to container Web UI (default: $WEB_PORT)
    --network NAME       Docker network for dev services (default: $DOCKER_NETWORK)
    --host-home DIR      Host home directory used to construct container mount paths
    -h, --help           Show this help

Env:
    HOST_HOME            Same as --host-home
    GOFRDOC_DOCKER_NETWORK  Same as --network
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --mcp-port)
            MCP_PORT="$2"; shift 2 ;;
        --mcpo-port)
            MCPO_PORT="$2"; shift 2 ;;
        --web-port)
            WEB_PORT="$2"; shift 2 ;;
        --network)
            DOCKER_NETWORK="$2"; shift 2 ;;
        --host-home)
            HOST_HOME="$2"; shift 2 ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [ -z "$HOST_HOME" ]; then
    host_user="${SUDO_USER:-$(id -un)}"
    host_home_from_passwd="$(getent passwd "$host_user" | cut -d: -f6 || true)"
    if [ -n "$host_home_from_passwd" ]; then
        HOST_HOME="$host_home_from_passwd"
    else
        HOST_HOME="${HOME:-/home/$host_user}"
    fi
fi

if [ ! -d "$HOST_HOME" ]; then
    echo "ERROR: host home directory does not exist: $HOST_HOME" >&2
    echo "  Provide a valid path via --host-home DIR" >&2
    exit 1
fi

CONTAINER_PROJECT_DIR="${HOST_HOME}/devroot/gofr-doc"
CONTAINER_DIG_DIR="${HOST_HOME}/devroot/gofr-dig"
CONTAINER_IQ_DIR="${HOST_HOME}/devroot/gofr-iq"
CONTAINER_PLOT_DIR="${HOST_HOME}/devroot/gofr-plot"

echo "======================================================================="
echo "Starting GOFR-DOC Development Container"
echo "======================================================================="
echo "Host user: $(id -un) (UID=${GOFR_UID}, GID=${GOFR_GID})"
echo "Host home: $HOST_HOME"
echo "Container will run with --user ${GOFR_UID}:${GOFR_GID}"
echo "Ports: MCP=$MCP_PORT, MCPO=$MCPO_PORT, Web=$WEB_PORT"
echo "Networks: $DOCKER_NETWORK, $TEST_NETWORK"
echo "======================================================================="

# Create docker networks if they don't exist
if ! docker network inspect "$DOCKER_NETWORK" >/dev/null 2>&1; then
    echo "Creating network: $DOCKER_NETWORK"
    docker network create "$DOCKER_NETWORK"
fi

if ! docker network inspect "$TEST_NETWORK" >/dev/null 2>&1; then
    echo "Creating network: $TEST_NETWORK"
    docker network create "$TEST_NETWORK"
fi

# Create docker volume for persistent data
VOLUME_NAME="gofr-doc-data-dev"
if ! docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
    echo "Creating volume: $VOLUME_NAME"
    docker volume create "$VOLUME_NAME"
fi

# Create shared secrets volume (shared across all GOFR projects)
SECRETS_VOLUME="gofr-secrets"
if ! docker volume inspect "$SECRETS_VOLUME" >/dev/null 2>&1; then
    echo "Creating volume: $SECRETS_VOLUME"
    docker volume create "$SECRETS_VOLUME"
fi

# Stop and remove existing container
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping existing container: $CONTAINER_NAME"
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# Detect Docker socket GID for group mapping
DOCKER_SOCKET="/var/run/docker.sock"
DOCKER_GID_ARGS=""
if [ -S "$DOCKER_SOCKET" ]; then
    DOCKER_GID=$(stat -c '%g' "$DOCKER_SOCKET")
    echo "Docker socket GID: $DOCKER_GID"
    DOCKER_GID_ARGS="-v $DOCKER_SOCKET:$DOCKER_SOCKET:rw --group-add $DOCKER_GID"
else
    echo "Warning: Docker socket not found at $DOCKER_SOCKET - docker commands will not work inside container"
fi

# ---- Pre-flight checks ------------------------------------------------------

# Verify image exists
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo ""
    echo "ERROR: Image '$IMAGE_NAME' not found."
    echo "  Build it first:  ./docker/build-dev.sh"
    echo ""
    exit 1
fi

# Ensure gofr-common submodule is initialised
COMMON_DIR="$PROJECT_ROOT/lib/gofr-common"
if [ ! -f "$COMMON_DIR/pyproject.toml" ]; then
    echo "gofr-common submodule not initialised -- initialising now..."
    cd "$PROJECT_ROOT"
    git submodule update --init --recursive
    if [ ! -f "$COMMON_DIR/pyproject.toml" ]; then
        echo ""
        echo "ERROR: Failed to initialise gofr-common submodule."
        echo "  $COMMON_DIR still has no pyproject.toml."
        echo "  Try manually: cd $PROJECT_ROOT && git submodule update --init --recursive"
        echo ""
        exit 1
    fi
    echo "gofr-common submodule initialised OK."
fi

# ---- Run container ----------------------------------------------------------
USER_ARGS="--user ${GOFR_UID}:${GOFR_GID}"

OPTIONAL_MOUNTS=()
if [ -d "$PROJECT_ROOT/../gofr-dig" ]; then
    OPTIONAL_MOUNTS+=("-v" "$PROJECT_ROOT/../gofr-dig:${CONTAINER_DIG_DIR}:ro")
fi
if [ -d "$PROJECT_ROOT/../gofr-iq" ]; then
    OPTIONAL_MOUNTS+=("-v" "$PROJECT_ROOT/../gofr-iq:${CONTAINER_IQ_DIR}:ro")
fi
if [ -d "$PROJECT_ROOT/../gofr-plot" ]; then
    OPTIONAL_MOUNTS+=("-v" "$PROJECT_ROOT/../gofr-plot:${CONTAINER_PLOT_DIR}:ro")
fi

echo "Running: docker run -d --name $CONTAINER_NAME ..."
CONTAINER_ID=$(docker run -d \
    --name "$CONTAINER_NAME" \
    --network "$DOCKER_NETWORK" \
    -w "${CONTAINER_PROJECT_DIR}" \
    $USER_ARGS \
    -p ${MCP_PORT}:8040 \
    -p ${MCPO_PORT}:8041 \
    -p ${WEB_PORT}:8042 \
    -v "$PROJECT_ROOT:${CONTAINER_PROJECT_DIR}:rw" \
    "${OPTIONAL_MOUNTS[@]}" \
    -v "${VOLUME_NAME}:${CONTAINER_PROJECT_DIR}/data:rw" \
    -v "${SECRETS_VOLUME}:/run/gofr-secrets:ro" \
    $DOCKER_GID_ARGS \
    -e GOFR_DOC_PROJECT_DIR="${CONTAINER_PROJECT_DIR}" \
    -e GOFRDOC_ENV=development \
    -e GOFRDOC_DEBUG=true \
    -e GOFRDOC_LOG_LEVEL=DEBUG \
    -e GOFR_DOC_AUTH_BACKEND=vault \
    -e GOFR_DOC_VAULT_URL=http://gofr-vault:8201 \
    -e GOFR_DOC_VAULT_PATH_PREFIX=gofr/auth \
    -e GOFR_DOC_VAULT_MOUNT=secret \
    "$IMAGE_NAME" 2>&1) || {
    echo ""
    echo "ERROR: docker run failed."
    echo "  Output: $CONTAINER_ID"
    echo ""
    exit 1
}

# ---- Verify container is actually running -----------------------------------
echo "Waiting for container to stabilise..."
sleep 2

# Connect to test network for Vault and other GOFR services
if ! docker network inspect "$TEST_NETWORK" --format '{{range .Containers}}{{.Name}} {{end}}' | grep -q "$CONTAINER_NAME"; then
    echo "Connecting to $TEST_NETWORK..."
    docker network connect "$TEST_NETWORK" "$CONTAINER_NAME"
fi

CONTAINER_STATE=$(docker inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "not_found")
CONTAINER_RUNNING=$(docker inspect --format '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null || echo "false")

if [[ "$CONTAINER_STATE" != "running" || "$CONTAINER_RUNNING" != "true" ]]; then
    EXIT_CODE=$(docker inspect --format '{{.State.ExitCode}}' "$CONTAINER_NAME" 2>/dev/null || echo "?")
    echo ""
    echo "======================================================================="
    echo "ERROR: Container '$CONTAINER_NAME' is NOT running"
    echo "======================================================================="
    echo "  State:     $CONTAINER_STATE"
    echo "  Exit code: $EXIT_CODE"
    echo ""
    echo "  Last 20 lines of container logs:"
    echo "  ---------------------------------"
    docker logs --tail 20 "$CONTAINER_NAME" 2>&1 | sed 's/^/  /'
    echo ""
    echo "  Full logs:  docker logs $CONTAINER_NAME"
    echo "  Inspect:    docker inspect $CONTAINER_NAME"
    echo ""
    exit 1
fi

# ---- Success ----------------------------------------------------------------
echo ""
echo "======================================================================="
echo "Container RUNNING: $CONTAINER_NAME"
echo "======================================================================="
echo "  ID:       ${CONTAINER_ID:0:12}"
echo "  State:    $CONTAINER_STATE"
echo "  Image:    $IMAGE_NAME"
echo "  Networks: $DOCKER_NETWORK, $TEST_NETWORK"
echo "  Docker:   $( [ -n "$DOCKER_GID_ARGS" ] && echo 'socket mounted (DinD ready)' || echo 'socket NOT mounted' )"
echo ""
echo "Ports:"
echo "  - $MCP_PORT -> 8040: MCP server"
echo "  - $MCPO_PORT -> 8041: MCPO proxy"
echo "  - $WEB_PORT -> 8042: Web interface"
echo ""
echo "Useful commands:"
echo "  docker logs -f $CONTAINER_NAME          # Follow logs"
echo "  docker exec -it $CONTAINER_NAME bash    # Shell access"
echo "  docker stop $CONTAINER_NAME             # Stop container"
