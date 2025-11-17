#!/bin/bash
# Build n8n Docker image

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

IMAGE_NAME="doco-n8n"
IMAGE_TAG="latest"

echo "Building n8n Docker image..."
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""

docker build \
    -f "${SCRIPT_DIR}/Dockerfile.n8n" \
    -t "${IMAGE_NAME}:${IMAGE_TAG}" \
    "${PROJECT_ROOT}"

echo ""
echo "Build complete: ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "To run n8n:"
echo "  ./docker/run-n8n.sh"
