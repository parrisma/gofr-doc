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
    -p $WEBUI_PORT:8080 \
    -e TZ="$TIMEZONE" \
    -v openwebui_volume:/data \
    -v "${WEBUI_SHARE_DIR}":/data/openwebui_share \
    ghcr.io/open-webui/open-webui:latest

if docker ps -q -f name=openwebui | grep -q .; then
    echo "Container openwebui is now running"
    echo ""
    echo "Open WebUI is accessible at http://localhost:$WEBUI_PORT"
    echo "On doco_net, other containers can reach it at http://openwebui:8080"
    echo "Data stored in Docker volume: openwebui_volume"
    echo "Shared directory: ${WEBUI_SHARE_DIR} -> /data/openwebui_share (inside container)"
    echo ""
    echo "To view logs: docker logs -f openwebui"
    echo "To stop: docker stop openwebui"
    echo "To recreate volume: ./docker/run-openwebui.sh -r"
else
    echo "ERROR: Container openwebui failed to start"
    docker logs openwebui
    exit 1
fi
