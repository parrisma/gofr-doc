#!/bin/sh

# Usage: ./run-openwebui.sh [-r] [-p PORT]
# Options:
#   -r         Recreate openwebui_volume (drop and recreate if it exists)
#   -p PORT    Port to expose Open WebUI on (default: 8080)
# Example: ./run-openwebui.sh -p 8090 -r

RECREATE_VOLUME=false
WEBUI_PORT=9090
while getopts "rp:" opt; do
    case $opt in
        r)
            RECREATE_VOLUME=true
            ;;
        p)
            WEBUI_PORT=$OPTARG
            ;;
        \?)
            echo "Usage: $0 [-r] [-p PORT]"
            echo "  -r         Recreate openwebui_volume (drop and recreate if it exists)"
            echo "  -p PORT    Port to expose Open WebUI on (default: 9090)"
            exit 1
            ;;
    esac
done

TIMEZONE="${TIMEZONE:-UTC}"

# Create openwebui_share directory on host if it doesn't exist
WEBUI_SHARE_DIR="${HOME}/openwebui_share"
echo "Checking for openwebui_share directory at ${WEBUI_SHARE_DIR}..."
if [ ! -d "$WEBUI_SHARE_DIR" ]; then
    echo "Creating openwebui_share directory..."
    mkdir -p "$WEBUI_SHARE_DIR"
    echo "Directory created at ${WEBUI_SHARE_DIR}"
else
    echo "Directory ${WEBUI_SHARE_DIR} already exists"
fi

# Create docker network if it doesn't exist
if ! docker network inspect doco_net >/dev/null 2>&1; then
    echo "Creating doco_net network..."
    docker network create doco_net
else
    echo "Network doco_net already exists"
fi

# Handle openwebui_volume creation/recreation
if [ "$RECREATE_VOLUME" = true ]; then
    echo "Recreate flag (-r) detected"
    if docker volume inspect openwebui_volume >/dev/null 2>&1; then
        echo "Removing existing openwebui_volume..."
        docker volume rm openwebui_volume 2>/dev/null || {
            echo "ERROR: Failed to remove openwebui_volume. It may be in use."
            echo "Stop all containers using the volume first."
            exit 1
        }
    fi
    echo "Creating openwebui_volume..."
    docker volume create openwebui_volume
else
    if ! docker volume inspect openwebui_volume >/dev/null 2>&1; then
        echo "Creating openwebui_volume..."
        docker volume create openwebui_volume
    else
        echo "Volume openwebui_volume already exists"
    fi
fi

# Stop and remove existing container if it exists
echo "Stopping existing openwebui container..."
docker stop openwebui 2>/dev/null || true

echo "Removing existing openwebui container..."
docker rm openwebui 2>/dev/null || true

echo "Starting openwebui container..."
echo "Port: $WEBUI_PORT"
docker run -d \
    --name openwebui \
    --network doco_net \
    -p 0.0.0.0:$WEBUI_PORT:8080 \
    -e TZ="$TIMEZONE" \
    -e WEBUI_AUTH=false \
    -v openwebui_volume:/data \
    -v "${WEBUI_SHARE_DIR}":/data/openwebui_share \
    --restart unless-stopped \
    ghcr.io/open-webui/open-webui:main

if docker ps -q -f name=openwebui | grep -q .; then
    echo "Container openwebui is now running"
    echo ""
    echo "==================================================================="
    echo "🌐 OPEN WEB UI ACCESS:"
    echo ""
    echo "From Your Browser (Host Machine):"
    echo "  👉 http://localhost:$WEBUI_PORT"
    echo ""
    echo "From WSL2 Host (Windows):"
    echo "  👉 http://\$(ip addr show eth0 | grep 'inet ' | awk '{print \$2}' | cut -d/ -f1):$WEBUI_PORT"
    echo ""
    echo "From Containers on doco_net:"
    echo "  http://openwebui:8080"
    echo ""
    echo "-------------------------------------------------------------------"
    echo "🔌 MCPO INTEGRATION (for Open WebUI settings):"
    echo ""
    echo "In Open WebUI Settings → Tools → Add OpenAPI Server:"
    echo "  URL:      http://\$(docker ps --filter 'name=.*dev' --format '{{.Names}}' | head -1):8000"
    echo "  API Key:  changeme"
    echo ""
    echo "Or use dev container hostname directly (run 'hostname' in dev container)"
    echo "  Example:  http://a8a8d018bc69:8000"
    echo ""
    echo "-------------------------------------------------------------------"
    echo "🔧 DIRECT ACCESS (from host machine):"
    echo "  MCPO Docs:     http://localhost:8000/docs"
    echo "  MCP Server:    http://localhost:8011/mcp"
    echo ""
    echo "Data & Storage:"
    echo "  Volume:        openwebui_volume"
    echo "  Shared Dir:    ${WEBUI_SHARE_DIR} -> /data/openwebui_share"
    echo ""
    echo "Management:"
    echo "  View logs:     docker logs -f openwebui"
    echo "  Stop:          docker stop openwebui"
    echo "  Recreate:      ./docker/run-openwebui.sh -r -p $WEBUI_PORT"
    echo "==================================================================="
    echo ""
else
    echo "ERROR: Container openwebui failed to start"
    docker logs openwebui
    exit 1
fi
