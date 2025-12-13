#!/bin/sh

# Usage: ./run-prod.sh [-n NETWORK] [-w WEB_PORT] [-m MCP_PORT]
# Defaults: NETWORK=gofr-net, WEB_PORT=8012, MCP_PORT=8010
# Example: ./run-prod.sh -n my-network -w 9012 -m 9010

# Default values (can be overridden by env vars or command line)
DOCKER_NETWORK="${GOFR_DOC_NETWORK:-gofr-net}"
WEB_PORT=8012
MCP_PORT=8010

# Parse command line arguments
while getopts "n:w:m:h" opt; do
    case $opt in
        n)
            DOCKER_NETWORK=$OPTARG
            ;;
        w)
            WEB_PORT=$OPTARG
            ;;
        m)
            MCP_PORT=$OPTARG
            ;;
        h)
            echo "Usage: $0 [-n NETWORK] [-w WEB_PORT] [-m MCP_PORT]"
            echo "  -n NETWORK   Docker network to attach to (default: gofr-net)"
            echo "  -w WEB_PORT  Port to expose web server on (default: 8012)"
            echo "  -m MCP_PORT  Port to expose MCP server on (default: 8010)"
            echo ""
            echo "Environment Variables:"
            echo "  GOFR_DOC_NETWORK  Default network (default: gofr-net)"
            exit 0
            ;;
        \?)
            echo "Usage: $0 [-n NETWORK] [-w WEB_PORT] [-m MCP_PORT]"
            exit 1
            ;;
    esac
done

# Create docker network if it doesn't exist
echo "Checking for ${DOCKER_NETWORK} network..."
if ! docker network inspect ${DOCKER_NETWORK} >/dev/null 2>&1; then
    echo "Creating ${DOCKER_NETWORK} network..."
    docker network create ${DOCKER_NETWORK}
else
    echo "Network ${DOCKER_NETWORK} already exists"
fi

# Create docker volume for persistent data if it doesn't exist
echo "Checking for gofr-doc_data volume..."
if ! docker volume inspect gofr-doc_data >/dev/null 2>&1; then
    echo "Creating gofr-doc_data volume..."
    docker volume create gofr-doc_data
    VOLUME_CREATED=true
else
    echo "Volume gofr-doc_data already exists"
    VOLUME_CREATED=false
fi

# Stop and remove existing container if it exists
echo "Stopping existing gofr-doc_prod container..."
docker stop gofr-doc_prod 2>/dev/null || true

echo "Removing existing gofr-doc_prod container..."
docker rm gofr-doc_prod 2>/dev/null || true

echo "Starting new gofr-doc_prod container..."
echo "Network: $DOCKER_NETWORK"
echo "Mounting gofr-doc_data volume to /home/gofr-doc/data in container"
echo "Web port: $WEB_PORT, MCP port: $MCP_PORT"

docker run -d \
--name gofr-doc_prod \
--network ${DOCKER_NETWORK} \
-v gofr-doc_data:/home/gofr-doc/data \
-p $WEB_PORT:8012 \
-p $MCP_PORT:8010 \
gofr-doc_prod:latest

if docker ps -q -f name=gofr-doc_prod | grep -q .; then
    echo "Container gofr-doc_prod is now running"
    
    # Fix volume permissions if it was just created
    if [ "$VOLUME_CREATED" = true ]; then
        echo "Fixing permissions on newly created volume..."
        docker exec -u root gofr-doc_prod chown -R gofr-doc:gofr-doc /home/gofr-doc/data
        echo "Volume permissions fixed"
    fi
    
    echo ""
    echo "HTTP REST API available at http://localhost:$WEB_PORT"
    echo "MCP Streamable HTTP Server available at http://localhost:$MCP_PORT/mcp/"
    echo "Persistent data stored in Docker volume: gofr-doc_data"
    echo ""
    echo "To run web server: docker exec -it gofr-doc_prod python -m app.main_web"
    echo "To view logs: docker logs -f gofr-doc_prod"
    echo "To stop: docker stop gofr-doc_prod"
else
    echo "ERROR: Container gofr-doc_prod failed to start"
    docker logs gofr-doc_prod
    exit 1
fi
