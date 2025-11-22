#!/bin/sh

# Usage: ./run-dev.sh [WEB_PORT] [MCP_PORT]
# Defaults: WEB_PORT=8010, MCP_PORT=8011
# Example: ./run-dev.sh 9010 9011

# Parse command line arguments
WEB_PORT=${1:-8010}
MCP_PORT=${2:-8011}

# Create docker network if it doesn't exist
echo "Checking for ai-net network..."
if ! docker network inspect ai-net >/dev/null 2>&1; then
    echo "Creating ai-net network..."
    docker network create ai-net
else
    echo "Network ai-net already exists"
fi

# Create docker volume for persistent data if it doesn't exist
echo "Checking for doco_data_dev volume..."
if ! docker volume inspect doco_data_dev >/dev/null 2>&1; then
    echo "Creating doco_data_dev volume..."
    docker volume create doco_data_dev
    VOLUME_CREATED=true
else
    echo "Volume doco_data_dev already exists"
    VOLUME_CREATED=false
fi

# Stop and remove existing container if it exists
echo "Stopping existing doco_dev container..."
docker stop doco_dev 2>/dev/null || true

echo "Removing existing doco_dev container..."
docker rm doco_dev 2>/dev/null || true

echo "Starting new doco_dev container..."
echo "Mounting $HOME/devroot/doco to /home/doco/devroot/doco in container"
echo "Mounting $HOME/.ssh to /home/doco/.ssh (read-only) in container"
echo "Mounting doco_data_dev volume to /home/doco/devroot/doco/data in container"
echo "Web port: $WEB_PORT, MCP port: $MCP_PORT"

docker run -d \
--name doco_dev \
--network ai-net \
--user $(id -u):$(id -g) \
-v "$HOME/devroot/doco":/home/doco/devroot/doco \
-v "$HOME/.ssh:/home/doco/.ssh:ro" \
-v doco_data_dev:/home/doco/devroot/doco/data \
-p $WEB_PORT:8010 \
-p $MCP_PORT:8011 \
doco_dev:latest

if docker ps -q -f name=doco_dev | grep -q .; then
    echo "Container doco_dev is now running"
    
    # Fix volume permissions if it was just created
    if [ "$VOLUME_CREATED" = true ]; then
        echo "Fixing permissions on newly created volume..."
        docker exec -u root doco_dev chown -R doco:doco /home/doco/devroot/doco/data
        echo "Volume permissions fixed"
    fi
    
    echo ""
    echo "==================================================================="
    echo "Development Container Access:"
    echo "  Shell:         docker exec -it doco_dev /bin/bash"
    echo "  VS Code:       Attach to container 'doco_dev'"
    echo ""
    echo "Access from Host Machine:"
    echo "  Web Server:    http://localhost:$WEB_PORT"
    echo "  MCP Server:    http://localhost:$MCP_PORT/mcp"
    echo ""
    echo "Access from ai-net (other containers):"
    echo "  Web Server:    http://doco_dev:8010"
    echo "  MCP Server:    http://doco_dev:8011/mcp"
    echo ""
    echo "Data & Storage:"
    echo "  Volume:        doco_data_dev"
    echo "  Source Mount:  $HOME/devroot/doco (live-reload)"
    echo "==================================================================="
    echo ""
else
    echo "ERROR: Container doco_dev failed to start"
    exit 1
fi