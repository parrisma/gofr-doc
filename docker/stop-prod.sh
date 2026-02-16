#!/bin/bash
# =======================================================================
# GOFR-DOC Production Stop Script
# =======================================================================
# Delegates to start-prod.sh --down.
# Usage:
#   ./docker/stop-prod.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/start-prod.sh" --down
