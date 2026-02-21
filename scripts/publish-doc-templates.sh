#!/bin/bash
# =============================================================================
# publish-doc-templates.sh -- Push local content into the running prod stack
# =============================================================================
# Copies templates, fragments, styles, and images from the local workspace
# into the gofr-doc-data volume (via a running container), then restarts
# the app containers so the YAML registries reload.
#
# No image rebuild required.
#
# Usage:
#   ./scripts/publish-doc-templates.sh                # publish all content
#   ./scripts/publish-doc-templates.sh --no-restart   # copy only, skip restart
#   ./scripts/publish-doc-templates.sh --dry-run      # show what would be copied
#   ./scripts/publish-doc-templates.sh --restart-only # restart without copying
#
# Content source:  app/content/{templates,fragments,styles,images}
# Volume target:   /home/gofr-doc/data/{templates,fragments,styles,images}
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source directory (canonical location in repo)
CONTENT_DIR="${PROJECT_ROOT}/app/content"

# Containers that mount the gofr-doc-data volume
COPY_TARGET="gofr-doc-mcp"
RESTART_CONTAINERS="gofr-doc-mcp gofr-doc-web"

# Remote base path inside container
REMOTE_DATA="/home/gofr-doc/data"

# Content subdirectories to sync
CONTENT_DIRS="templates fragments styles images"

# -- Parse arguments ----------------------------------------------------------
DRY_RUN=false
NO_RESTART=false
RESTART_ONLY=false

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)       DRY_RUN=true; shift ;;
        --no-restart)    NO_RESTART=true; shift ;;
        --restart-only)  RESTART_ONLY=true; shift ;;
        --help|-h)
            sed -n '/^# Usage:/,/^# ====/p' "$0" | head -n -1 | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            exit 1
            ;;
    esac
done

# -- Preflight checks --------------------------------------------------------
if ! docker ps -q -f name="${COPY_TARGET}" | grep -q .; then
    echo "ERROR: Container ${COPY_TARGET} is not running."
    echo "Start the prod stack first:  ./docker/start-prod.sh"
    exit 1
fi

if [ ! -d "${CONTENT_DIR}" ]; then
    echo "ERROR: Content directory not found: ${CONTENT_DIR}"
    exit 1
fi

# -- Copy content -------------------------------------------------------------
if [ "$RESTART_ONLY" = false ]; then
    echo "=== Publishing doc content to ${COPY_TARGET} ==="

    copied=0
    skipped=0

    for subdir in ${CONTENT_DIRS}; do
        src="${CONTENT_DIR}/${subdir}"
        dst="${REMOTE_DATA}/${subdir}"

        if [ ! -d "${src}" ]; then
            echo "  [SKIP] ${subdir}/ (not found locally)"
            skipped=$((skipped + 1))
            continue
        fi

        # Count files to copy
        file_count=$(find "${src}" -type f | wc -l)
        if [ "${file_count}" -eq 0 ]; then
            echo "  [SKIP] ${subdir}/ (empty)"
            skipped=$((skipped + 1))
            continue
        fi

        if [ "$DRY_RUN" = true ]; then
            echo "  [DRY]  ${subdir}/ (${file_count} files)"
            find "${src}" -type f -printf "           %P\n"
        else
            # docker cp merges into existing directory without deleting extras
            docker cp "${src}/." "${COPY_TARGET}:${dst}/"
            echo "  [OK]   ${subdir}/ (${file_count} files)"
        fi
        copied=$((copied + 1))
    done

    echo ""
    echo "Content dirs copied: ${copied}, skipped: ${skipped}"

    if [ "$DRY_RUN" = true ]; then
        echo "(dry run -- nothing was changed)"
        exit 0
    fi
fi

# -- Restart containers -------------------------------------------------------
if [ "$NO_RESTART" = true ]; then
    echo ""
    echo "Skipping restart (--no-restart)."
    echo "NOTE: YAML schema changes will not take effect until containers restart."
    echo "  Jinja2 template changes (.html.jinja2) are picked up on next render."
    echo "  To restart later:  $0 --restart-only"
    exit 0
fi

# Prompt unless --restart-only was passed (explicit intent to restart)
if [ "$RESTART_ONLY" = false ] && [ -t 0 ]; then
    echo ""
    read -r -p "Restart containers now? [Y/n] " answer
    case "${answer}" in
        [nN]*)
            echo ""
            echo "Restart skipped. To restart later:"
            echo "  $0 --restart-only"
            exit 0
            ;;
    esac
fi

echo ""
echo "Restarting app containers..."
for ctr in ${RESTART_CONTAINERS}; do
    if docker ps -q -f name="${ctr}" | grep -q .; then
        docker restart "${ctr}" >/dev/null
        echo "  [OK]   ${ctr} restarted"
    else
        echo "  [SKIP] ${ctr} (not running)"
    fi
done

# -- Quick health check -------------------------------------------------------
echo ""
echo "Waiting for services..."
sleep 4

all_ok=true
for ctr in ${RESTART_CONTAINERS}; do
    if docker ps -q -f name="${ctr}" | grep -q .; then
        echo "  [OK]   ${ctr} running"
    else
        echo "  [ERR]  ${ctr} NOT running"
        all_ok=false
    fi
done

echo ""
if [ "$all_ok" = true ]; then
    echo "=== Content published successfully ==="
else
    echo "WARNING: Some containers failed to restart. Check logs:"
    echo "  docker logs gofr-doc-mcp --tail 30"
    exit 1
fi
