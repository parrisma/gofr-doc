#!/bin/bash
# Token Manager CLI Wrapper
# Provides environment-aware access to JWT token management
#
# Usage:
#   ./token_manager.sh [--env PROD|TEST] <command> [options]
#
# Examples:
#   ./token_manager.sh create --group research --expires 3600  # Uses current env
#   ./token_manager.sh --env PROD list                         # Force PROD environment
#   ./token_manager.sh --env TEST verify --token <token>       # Force TEST environment

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
uv run python -m app.management.token_manager \
    --gofr-doc-env "$GOFR_DOC_ENV" \
    --token-store "$GOFR_DOC_TOKEN_STORE" \
    "$@"
