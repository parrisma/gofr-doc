#!/bin/bash
# Storage Manager CLI Wrapper
# Provides environment-aware access to storage and sessions management
#
# Usage:
#   ./storage_manager.sh [--env PROD|TEST] <resource> <command> [options]
#
# Examples:
#   ./storage_manager.sh sessions list                    # Uses current GOFR_DOC_ENV
#   ./storage_manager.sh --env PROD storage stats         # Force PROD environment
#   ./storage_manager.sh --env TEST sessions purge --yes  # Force TEST environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source centralized configuration (defaults to TEST)
source "$SCRIPT_DIR/gofr-doc.env"

# Parse --env flag if provided as first argument
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            export GOFR_DOC_ENV="$2"
            shift 2
            ;;
        *)
            break
            ;;
    esac
done

# Re-source gofr-doc.env with potentially updated GOFR_DOC_ENV to pick up correct paths
source "$SCRIPT_DIR/gofr-doc.env"

# Call Python module with environment variables as CLI args
cd "$GOFR_DOC_ROOT"
uv run python -m app.management.storage_manager \
    --gofr-doc-env "$GOFR_DOC_ENV" \
    --data-root "$GOFR_DOC_DATA" \
    --token-store "$GOFR_DOC_TOKEN_STORE" \
    "$@"
