#!/bin/bash
# Render Manager CLI Wrapper
# Provides environment-aware access to template and fragment management
#
# Usage:
#   ./render_manager.sh [--env PROD|TEST] <resource> <command> [options]
#
# Examples:
#   ./render_manager.sh templates list                    # Uses current env
#   ./render_manager.sh --env PROD groups                 # Force PROD environment
#   ./render_manager.sh --env TEST fragments list -v      # Force TEST environment

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
uv run python -m app.management.render_manager \
    --gofr-doc-env "$GOFR_DOC_ENV" \
    --data-root "$GOFR_DOC_DATA" \
    "$@"
