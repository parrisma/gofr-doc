#!/bin/sh

# Usage: ./run-prod.sh [WEB_PORT] [MCP_PORT]
# Defaults: WEB_PORT=8012, MCP_PORT=8010
# Example: ./run-prod.sh 9012 9010

# Parse command line arguments
WEB_PORT=${1:-8012}
MCP_PORT=${2:-8010}

# Create docker network if it doesn't exist
echo "Checking for ai-net network..."
if ! docker network inspect ai-net >/dev/null 2>&1; then
    echo "Creating ai-net network..."
    docker network create ai-net
else
    echo "Network ai-net already exists"
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
--network ai-net \
-v doco_data:/home/doco/data \
-p $WEB_PORT:8012 \
-p $MCP_PORT:8010 \
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
    echo "==================================================================="
    echo "Access from Host Machine:"
    echo "  Web Server:    http://localhost:$WEB_PORT"
    echo "  MCP Server:    http://localhost:$MCP_PORT/mcp"
    echo ""
    echo "Access from ai-net (other containers):"
    echo "  Web Server:    http://doco_prod:8012"
    echo "  MCP Server:    http://doco_prod:8010/mcp"
    echo ""
    echo "Data & Storage:"
    echo "  Volume:        doco_data"
    echo ""
    echo "Management:"
    echo "  Run web:       docker exec -it doco_prod python -m app.main_web"
    echo "  View logs:     docker logs -f doco_prod"
    echo "  Stop:          docker stop doco_prod"
    echo "==================================================================="
    echo ""
else
    echo "ERROR: Container doco_prod failed to start"
    docker logs doco_prod
    exit 1
fi
