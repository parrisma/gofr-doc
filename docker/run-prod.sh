#!/bin/bash
# Run gofr-doc production container with proper volumes and networking
set -e

CONTAINER_NAME="gofr-doc-prod"
IMAGE_NAME="gofr-doc-prod:latest"
NETWORK_NAME="gofr-net"

# Port assignments for gofr-doc
MCP_PORT="${GOFR_DOC_MCP_PORT:-8040}"
MCPO_PORT="${GOFR_DOC_MCPO_PORT:-8041}"
WEB_PORT="${GOFR_DOC_WEB_PORT:-8042}"

echo "=== gofr-doc Production Container ==="

# Create network if it doesn't exist
if ! docker network inspect ${NETWORK_NAME} >/dev/null 2>&1; then
    echo "Creating network: ${NETWORK_NAME}"
    docker network create ${NETWORK_NAME}
fi

# Create volumes if they don't exist
for vol in gofr-doc-data gofr-doc-logs; do
    if ! docker volume inspect ${vol} >/dev/null 2>&1; then
        echo "Creating volume: ${vol}"
        docker volume create ${vol}
    fi
done

# Stop existing container if running
if docker ps -q -f name=${CONTAINER_NAME} | grep -q .; then
    echo "Stopping existing container..."
    docker stop ${CONTAINER_NAME}
fi

# Remove existing container if exists
if docker ps -aq -f name=${CONTAINER_NAME} | grep -q .; then
    echo "Removing existing container..."
    docker rm ${CONTAINER_NAME}
fi

echo "Starting ${CONTAINER_NAME}..."
echo "  MCP Port:  ${MCP_PORT}"
echo "  MCPO Port: ${MCPO_PORT}"
echo "  Web Port:  ${WEB_PORT}"

docker run -d \
    --name ${CONTAINER_NAME} \
    --network ${NETWORK_NAME} \
    -v gofr-doc-data:/home/gofr-doc/data \
    -v gofr-doc-logs:/home/gofr-doc/logs \
    -v gofr-secrets:/run/gofr-secrets:ro \
    -p ${MCP_PORT}:8040 \
    -p ${MCPO_PORT}:8041 \
    -p ${WEB_PORT}:8042 \
    -e GOFR_DOC_AUTH_BACKEND=vault \
    -e GOFR_DOC_VAULT_URL=http://gofr-vault:8201 \
    -e GOFR_DOC_VAULT_PATH_PREFIX=gofr/doc/auth \
    -e GOFR_DOC_VAULT_MOUNT=secret \
    ${IMAGE_NAME}

# Wait for container to start
sleep 2

if docker ps -q -f name=${CONTAINER_NAME} | grep -q .; then
    echo ""
    echo "=== Container Started Successfully ==="
    echo "MCP Server:  http://localhost:${MCP_PORT}/mcp"
    echo "MCPO Server: http://localhost:${MCPO_PORT}"
    echo "Web Server:  http://localhost:${WEB_PORT}"
    echo ""
    echo "Volumes:"
    echo "  Data: gofr-doc-data"
    echo "  Logs: gofr-doc-logs"
    echo ""
    echo "Commands:"
    echo "  Logs:   docker logs -f ${CONTAINER_NAME}"
    echo "  Stop:   ./stop-prod.sh"
    echo "  Shell:  docker exec -it ${CONTAINER_NAME} bash"
else
    echo "ERROR: Container failed to start"
    docker logs ${CONTAINER_NAME}
    exit 1
fi
