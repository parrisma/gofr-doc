#!/bin/bash
set -e

# Fix data directory permissions if mounted as volume
if [ -d "/home/doco/devroot/doco/data" ]; then
    # Check if we can write to data directory
    if [ ! -w "/home/doco/devroot/doco/data" ]; then
        echo "Fixing permissions for /home/doco/devroot/doco/data..."
        # This will work if container is started with appropriate privileges
        sudo chown -R doco:doco /home/doco/devroot/doco/data 2>/dev/null || \
            echo "Warning: Could not fix permissions. Run container with --user $(id -u):$(id -g)"
    fi
fi

# Create subdirectories if they don't exist
mkdir -p /home/doco/devroot/doco/data/storage /home/doco/devroot/doco/data/auth

# Install/sync Python dependencies if requirements.txt exists
if [ -f "/home/doco/devroot/doco/requirements.txt" ]; then
    echo "Installing Python dependencies..."
    cd /home/doco/devroot/doco
    # Use 'uv pip install' instead of 'sync' to ensure transitive dependencies are installed
    VIRTUAL_ENV=/home/doco/devroot/doco/.venv uv pip install -r requirements.txt || \
        echo "Warning: Could not install dependencies"
fi

# Execute the main command
exec "$@"
