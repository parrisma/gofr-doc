#!/bin/sh

# Usage: ./run-prod.sh [WEB_PORT] [MCP_PORT]
# Defaults: WEB_PORT=8010, MCP_PORT=8011
# Example: ./run-prod.sh 9010 9011

# Parse command line arguments
WEB_PORT=${1:-8010}
MCP_PORT=${2:-8011}

# Create docker network if it doesn't exist
echo "Checking for doco_net network..."
if ! docker network inspect doco_net >/dev/null 2>&1; then
    echo "Creating doco_net network..."
    docker network create doco_net
else
    echo "Network doco_net already exists"
fi

# Create docker volume for persistent data if it doesn't exist
echo "Checking for doco_data volume..."
if ! docker volume inspect doco_data >/dev/null 2>&1; then
    echo "Creating doco_data volume..."
    docker volume create doco_data
    VOLUME_CREATED=true
else
    echo "Volume doco_data already exists"
    VOLUME_CREATED=false
fi

# Stop and remove existing container if it exists
echo "Stopping existing doco_prod container..."
docker stop doco_prod 2>/dev/null || true

echo "Removing existing doco_prod container..."
docker rm doco_prod 2>/dev/null || true

echo "Starting new doco_prod container..."
echo "Mounting doco_data volume to /home/doco/data in container"
echo "Web port: $WEB_PORT, MCP port: $MCP_PORT"

docker run -d \
--name doco_prod \
--network doco_net \
-v doco_data:/home/doco/data \
-p $WEB_PORT:8010 \
-p $MCP_PORT:8011 \
doco_prod:latest

if docker ps -q -f name=doco_prod | grep -q .; then
    echo "Container doco_prod is now running"
    
    # Fix volume permissions if it was just created
    if [ "$VOLUME_CREATED" = true ]; then
        echo "Fixing permissions on newly created volume..."
        docker exec -u root doco_prod chown -R doco:doco /home/doco/data
        echo "Volume permissions fixed"
    fi
    
    echo ""
    echo "HTTP REST API available at http://localhost:$WEB_PORT"
    echo "MCP Streamable HTTP Server available at http://localhost:$MCP_PORT/mcp/"
    echo "Persistent data stored in Docker volume: doco_data"
    echo ""
    echo "To run web server: docker exec -it doco_prod python -m app.main_web"
    echo "To view logs: docker logs -f doco_prod"
    echo "To stop: docker stop doco_prod"
else
    echo "ERROR: Container doco_prod failed to start"
    docker logs doco_prod
    exit 1
fi
