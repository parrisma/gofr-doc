#!/bin/sh

# Usage: ./run-prod.sh [WEB_PORT] [MCP_PORT] [NETWORK]
# Defaults: WEB_PORT=8002, MCP_PORT=8000, NETWORK=gofr-net
# Example: ./run-prod.sh 9012 9010 my-network

# Parse command line arguments
WEB_PORT=${1:-8002}
MCP_PORT=${2:-8000}
NETWORK=${3:-${GOFR_DOC_NETWORK:-gofr-net}}

# Create docker network if it doesn't exist
echo "Checking for $NETWORK network..."
if ! docker network inspect $NETWORK >/dev/null 2>&1; then
    echo "Creating $NETWORK network..."
    docker network create $NETWORK
else
    echo "Network $NETWORK already exists"
fi

# Create docker volume for persistent data if it doesn't exist
echo "Checking for gofr-doc-data volume..."
if ! docker volume inspect gofr-doc-data >/dev/null 2>&1; then
    echo "Creating gofr-doc-data volume..."
    docker volume create gofr-doc-data
    VOLUME_CREATED=true
else
    echo "Volume gofr-doc-data already exists"
    VOLUME_CREATED=false
fi

# Stop and remove existing container if it exists
echo "Stopping existing gofr-doc-prod container..."
docker stop gofr-doc-prod 2>/dev/null || true

echo "Removing existing gofr-doc-prod container..."
docker rm gofr-doc-prod 2>/dev/null || true

echo "Starting new gofr-doc-prod container..."
echo "Mounting gofr-doc-data volume to /home/gofr-doc/data in container"
echo "Web port: $WEB_PORT, MCP port: $MCP_PORT"

docker run -d \
--name gofr-doc-prod \
--network $NETWORK \
-v gofr-doc-data:/home/gofr-doc/data \
-p $WEB_PORT:8002 \
-p $MCP_PORT:8000 \
gofr-doc-prod:latest

if docker ps -q -f name=gofr-doc-prod | grep -q .; then
    echo "Container gofr-doc-prod is now running"
    
    # Fix volume permissions if it was just created
    if [ "$VOLUME_CREATED" = true ]; then
        echo "Fixing permissions on newly created volume..."
        docker exec -u root gofr-doc-prod chown -R gofr-doc:gofr-doc /home/gofr-doc/data
        echo "Volume permissions fixed"
    fi
    
    echo ""
    echo "==================================================================="
    echo "Access from Host Machine:"
    echo "  Web Server:    http://localhost:$WEB_PORT"
    echo "  MCP Server:    http://localhost:$MCP_PORT/mcp"
    echo ""
    echo "Access from $NETWORK (other containers):"
    echo "  Web Server:    http://gofr-doc-prod:8002"
    echo "  MCP Server:    http://gofr-doc-prod:8000/mcp"
    echo ""
    echo "Data & Storage:"
    echo "  Volume:        gofr-doc-data"
    echo ""
    echo "Management:"
    echo "  Run web:       docker exec -it gofr-doc-prod python -m app.main_web"
    echo "  View logs:     docker logs -f gofr-doc-prod"
    echo "  Stop:          docker stop gofr-doc-prod"
    echo "==================================================================="
    echo ""
else
    echo "ERROR: Container gofr-doc-prod failed to start"
    docker logs gofr-doc-prod
    exit 1
fi
