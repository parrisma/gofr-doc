#!/bin/sh

# Usage: ./run-dev.sh [WEB_PORT] [MCP_PORT] [MCPO_PORT]
# Defaults: WEB_PORT=8012, MCP_PORT=8010, MCPO_PORT=8011
# Example: ./run-dev.sh 9012 9010 9011

# Parse command line arguments
WEB_PORT=${1:-8012}
MCP_PORT=${2:-8010}
MCPO_PORT=${3:-8011}

# Create docker network if it doesn't exist
echo "Checking for ai-net network..."
if ! docker network inspect ai-net >/dev/null 2>&1; then
    echo "Creating ai-net network..."
    docker network create ai-net
else
    echo "Network ai-net already exists"
fi

# Create docker volume for persistent data if it doesn't exist
echo "Checking for gofr-doc-data-dev volume..."
if ! docker volume inspect gofr-doc-data-dev >/dev/null 2>&1; then
    echo "Creating gofr-doc-data-dev volume..."
    docker volume create gofr-doc-data-dev
    VOLUME_CREATED=true
else
    echo "Volume gofr-doc-data-dev already exists"
    VOLUME_CREATED=false
fi

# Stop and remove existing container if it exists
echo "Stopping existing gofr-doc-dev container..."
docker stop gofr-doc-dev 2>/dev/null || true

echo "Removing existing gofr-doc-dev container..."
docker rm gofr-doc-dev 2>/dev/null || true

echo "Starting new gofr-doc-dev container..."
echo "Mounting $HOME/devroot/gofr-doc to /home/gofr-doc/devroot/gofr-doc in container"
echo "Mounting $HOME/.ssh to /home/gofr-doc/.ssh (read-only) in container"
echo "Mounting gofr-doc-data-dev volume to /home/gofr-doc/devroot/gofr-doc/data in container"
echo "Web port: $WEB_PORT, MCP port: $MCP_PORT, MCPO port: $MCPO_PORT"

docker run -d \
--name gofr-doc-dev \
--network ai-net \
--user $(id -u):$(id -g) \
-v "$HOME/devroot/gofr-doc":/home/gofr-doc/devroot/gofr-doc \
-v "$HOME/.ssh:/home/gofr-doc/.ssh:ro" \
-v gofr-doc-data-dev:/home/gofr-doc/devroot/gofr-doc/data \
-p $MCP_PORT:8010 \
-p $MCPO_PORT:8011 \
-p $WEB_PORT:8012 \
gofr-doc-dev:latest

if docker ps -q -f name=gofr-doc-dev | grep -q .; then
    echo "Container gofr-doc-dev is now running"
    
    # Fix volume permissions if it was just created
    if [ "$VOLUME_CREATED" = true ]; then
        echo "Fixing permissions on newly created volume..."
        docker exec -u root gofr-doc-dev chown -R gofr-doc:gofr-doc /home/gofr-doc/devroot/gofr-doc/data
        echo "Volume permissions fixed"
    fi
    
    echo ""
    echo "==================================================================="
    echo "Development Container Access:"
    echo "  Shell:         docker exec -it gofr-doc-dev /bin/bash"
    echo "  VS Code:       Attach to container 'gofr-doc-dev'"
    echo ""
    echo "Access from Host Machine:"
    echo "  Web Server:    http://localhost:$WEB_PORT"
    echo "  MCP Server:    http://localhost:$MCP_PORT/mcp"
    echo "  MCPO Proxy:    http://localhost:$MCPO_PORT"
    echo ""
    echo "Access from ai-net (other containers):"
    echo "  Web Server:    http://gofr-doc-dev:8012"
    echo "  MCP Server:    http://gofr-doc-dev:8010/mcp"
    echo "  MCPO Proxy:    http://gofr-doc-dev:8011"
    echo ""
    echo "Data & Storage:"
    echo "  Volume:        gofr-doc-data-dev"
    echo "  Source Mount:  $HOME/devroot/gofr-doc (live-reload)"
    echo "==================================================================="
    echo ""
else
    echo "ERROR: Container gofr-doc-dev failed to start"
    exit 1
fi