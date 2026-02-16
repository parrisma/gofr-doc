#!/bin/bash
# =======================================================================
# GOFR-DOC Production Stop Script
# =======================================================================
# Stops the compose-based production stack.
# Usage:
#   ./docker/stop-prod.sh         # Stop all services
#   ./docker/stop-prod.sh --rm    # Stop and remove containers + orphans

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/compose.prod.yml"

echo "Stopping gofr-doc production stack..."

if [ "$1" = "--rm" ] || [ "$1" = "-r" ]; then
    docker compose -f "$COMPOSE_FILE" down --remove-orphans
    echo "Stack stopped and containers removed."
else
    docker compose -f "$COMPOSE_FILE" stop
    echo "Stack stopped (containers preserved)."
fi
