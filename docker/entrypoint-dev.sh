#!/bin/bash
set -e

# Fix data directory permissions if mounted as volume
if [ -d "/home/gofr-doc/devroot/gofr-doc/data" ]; then
    # Check if we can write to data directory
    if [ ! -w "/home/gofr-doc/devroot/gofr-doc/data" ]; then
        echo "Fixing permissions for /home/gofr-doc/devroot/gofr-doc/data..."
        # This will work if container is started with appropriate privileges
        sudo chown -R gofr-doc:gofr-doc /home/gofr-doc/devroot/gofr-doc/data 2>/dev/null || \
            echo "Warning: Could not fix permissions. Run container with --user $(id -u):$(id -g)"
    fi
fi

# Create subdirectories if they don't exist
mkdir -p /home/gofr-doc/devroot/gofr-doc/data/storage /home/gofr-doc/devroot/gofr-doc/data/auth

# Install/sync Python dependencies if requirements.txt exists
if [ -f "/home/gofr-doc/devroot/gofr-doc/requirements.txt" ]; then
    echo "Installing Python dependencies..."
    cd /home/gofr-doc/devroot/gofr-doc
    # Use 'uv pip install' instead of 'sync' to ensure transitive dependencies are installed
    VIRTUAL_ENV=/home/gofr-doc/devroot/gofr-doc/.venv uv pip install -r requirements.txt || \
        echo "Warning: Could not install dependencies"
fi

# Execute the main command
exec "$@"
