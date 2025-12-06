#!/bin/bash
# Stop all DOCO servers and verify they are completely terminated
# Stops: MCP, MCPO, Web, n8n, OpenWebUI

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MCP_PORT=8000
MCPO_PORT=8001
WEB_PORT=8002

# Logging
LOG_FILE="/tmp/gofr-doc_stop_servers.log"
echo "=== Stopping DOCO Servers at $(date) ===" > "$LOG_FILE"

# Helper functions
log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
    echo "[$(date '+%H:%M:%S')] $1" >> "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
    echo "✓ $1" >> "$LOG_FILE"
}

error() {
    echo -e "${RED}✗${NC} $1"
    echo "✗ $1" >> "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    echo "⚠ $1" >> "$LOG_FILE"
}

# Kill process by pattern and verify
kill_process() {
    local name=$1
    local pattern=$2
    local max_attempts=${3:-10}
    
    log "Stopping $name..."
    
    # Find and kill processes
    local pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    
    if [ -z "$pids" ]; then
        warn "$name was not running"
        return 0
    fi
    
    # Try graceful shutdown first (SIGTERM)
    echo "$pids" | xargs kill -TERM 2>/dev/null || true
    
    # Wait and verify termination
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        pids=$(pgrep -f "$pattern" 2>/dev/null || true)
        if [ -z "$pids" ]; then
            success "$name stopped"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 0.5
    done
    
    # Force kill if still running (SIGKILL)
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        warn "$name not responding, force killing..."
        echo "$pids" | xargs kill -KILL 2>/dev/null || true
        sleep 1
        
        # Final verification
        pids=$(pgrep -f "$pattern" 2>/dev/null || true)
        if [ -z "$pids" ]; then
            success "$name force stopped"
            return 0
        else
            error "$name could not be stopped (PIDs: $pids)"
            return 1
        fi
    fi
}

# Stop Docker container and verify
stop_container() {
    local name=$1
    local max_attempts=${2:-10}
    
    log "Stopping container $name..."
    
    # Check if docker is available
    if ! command -v docker &> /dev/null; then
        warn "Docker not available in this environment - container $name should be stopped from host"
        return 0
    fi
    
    # Check if container exists
    if ! docker ps -a -q -f name="^${name}$" | grep -q .; then
        warn "Container $name does not exist"
        return 0
    fi
    
    # Stop container
    docker stop "$name" >> "$LOG_FILE" 2>&1 || true
    
    # Wait and verify
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if ! docker ps -q -f name="^${name}$" | grep -q .; then
            success "Container $name stopped"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    # Force remove if still running
    if docker ps -q -f name="^${name}$" | grep -q .; then
        warn "Container $name not responding, force removing..."
        docker rm -f "$name" >> "$LOG_FILE" 2>&1 || true
        sleep 1
        
        # Final verification
        if ! docker ps -a -q -f name="^${name}$" | grep -q .; then
            success "Container $name force removed"
            return 0
        else
            error "Container $name could not be stopped"
            return 1
        fi
    fi
}

# Verify port is free
verify_port_free() {
    local name=$1
    local port=$2
    
    if lsof -i ":$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
        local pid=$(lsof -i ":$port" -sTCP:LISTEN -t 2>/dev/null || true)
        error "Port $port still in use by process $pid ($name)"
        return 1
    else
        success "Port $port is free ($name)"
        return 0
    fi
}

# Main shutdown sequence
echo ""
echo "================================================================"
echo "  Stopping DOCO Server Stack"
echo "================================================================"
echo ""

ERRORS=0

# Stop all servers (order doesn't matter for shutdown)
# 1. MCP Server
kill_process "MCP Server" "main_mcp.py" || ERRORS=$((ERRORS + 1))

# 2. MCPO
kill_process "MCPO" "mcpo.*--port $MCPO_PORT" || ERRORS=$((ERRORS + 1))

# 3. Web Server
kill_process "Web Server" "main_web.py" || ERRORS=$((ERRORS + 1))

# 4. n8n container
stop_container "n8n" || ERRORS=$((ERRORS + 1))

# 5. OpenWebUI container
stop_container "openwebui" || ERRORS=$((ERRORS + 1))

echo ""
log "Verifying all services are stopped..."
echo ""

# Verify ports are free
VERIFY_ERRORS=0
verify_port_free "MCP" $MCP_PORT || VERIFY_ERRORS=$((VERIFY_ERRORS + 1))
verify_port_free "MCPO" $MCPO_PORT || VERIFY_ERRORS=$((VERIFY_ERRORS + 1))
verify_port_free "Web" $WEB_PORT || VERIFY_ERRORS=$((VERIFY_ERRORS + 1))

# Additional process verification
log "Double-checking for any remaining processes..."
remaining=$(pgrep -f "main_mcp.py|main_web.py|mcpo.*--port" 2>/dev/null || true)
if [ -n "$remaining" ]; then
    error "Some processes still running: $remaining"
    VERIFY_ERRORS=$((VERIFY_ERRORS + 1))
else
    success "No remaining Python server processes"
fi

# Container verification
log "Verifying containers are stopped..."
if command -v docker &> /dev/null; then
    if docker ps -q -f name="^n8n$" | grep -q .; then
        error "Container n8n still running"
        VERIFY_ERRORS=$((VERIFY_ERRORS + 1))
    else
        success "Container n8n stopped"
    fi

    if docker ps -q -f name="^openwebui$" | grep -q .; then
        error "Container openwebui still running"
        VERIFY_ERRORS=$((VERIFY_ERRORS + 1))
    else
        success "Container openwebui stopped"
    fi
else
    warn "Docker not available - cannot verify container status"
    echo "  (Run this script from host to manage Docker containers)"
fi

echo ""
echo "================================================================"
if [ $ERRORS -eq 0 ] && [ $VERIFY_ERRORS -eq 0 ]; then
    success "All servers stopped successfully and verified!"
    echo "================================================================"
    echo ""
    echo "📊 Final Status:"
    echo "  ✓ All processes terminated"
    echo "  ✓ All ports released"
    echo "  ✓ All containers stopped"
    echo ""
    echo "📝 Log: $LOG_FILE"
    echo "🚀 To restart: bash scripts/start_all_servers.sh"
    echo "================================================================"
    echo ""
    exit 0
else
    error "Some servers could not be stopped cleanly"
    echo "================================================================"
    echo ""
    echo "⚠️  Issues detected:"
    echo "  Stop errors:       $ERRORS"
    echo "  Verification errors: $VERIFY_ERRORS"
    echo ""
    echo "📝 Check log: $LOG_FILE"
    echo ""
    echo "Manual cleanup commands:"
    echo "  Kill processes:    pkill -9 -f 'main_mcp.py|main_web.py|mcpo'"
    echo "  Stop containers:   docker stop n8n openwebui && docker rm n8n openwebui"
    echo "  Check ports:       lsof -i :8000 -i :8001 -i :8002 -i :5678 -i :9090"
    echo "================================================================"
    echo ""
    exit 1
fi
