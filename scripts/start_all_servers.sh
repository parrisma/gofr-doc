#!/bin/bash
# Start all DOCO servers in order with verification
# Servers: MCP (8000) -> MCPO (8001) -> Web (8002) -> n8n (5678) -> OpenWebUI (9090)

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
N8N_PORT=5678
OPENWEBUI_PORT=9090

# Logging
LOG_FILE="/tmp/gofr-doc_start_servers.log"
echo "=== Starting DOCO Servers at $(date) ===" > "$LOG_FILE"

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

# Check if server is responding
check_server() {
    local name=$1
    local url=$2
    local max_attempts=${3:-30}
    local attempt=0
    
    log "Waiting for $name to be ready..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -o /dev/null -w "%{http_code}" "$url" 2>&1 | grep -q "200\|404\|405"; then
            success "$name is ready at $url"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    error "$name failed to start within ${max_attempts} seconds"
    return 1
}

# Check if Docker container is running
check_container() {
    local name=$1
    local max_attempts=${2:-30}
    local attempt=0
    
    # Check if docker is available
    if ! command -v docker &> /dev/null; then
        warn "Docker not available in this environment - skipping container check for $name"
        warn "Container $name should be managed from the host machine"
        return 0
    fi
    
    log "Waiting for container $name..."
    while [ $attempt -lt $max_attempts ]; do
        if docker ps -q -f name="^${name}$" | grep -q .; then
            if docker ps -f name="^${name}$" --format "{{.Status}}" | grep -q "Up"; then
                success "Container $name is running"
                return 0
            fi
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    error "Container $name failed to start within ${max_attempts} seconds"
    return 1
}

# Main startup sequence
echo ""
echo "================================================================"
echo "  Starting DOCO Server Stack"
echo "================================================================"
echo ""

# 1. MCP Server (8000)
log "Step 1/5: Starting MCP Server on port $MCP_PORT"
bash scripts/run_mcp.sh >> "$LOG_FILE" 2>&1 &
if check_server "MCP Server" "http://localhost:$MCP_PORT/" 30; then
    echo ""
else
    error "MCP Server failed to start. Check $LOG_FILE"
    exit 1
fi

# 2. MCPO (8001) - depends on MCP
log "Step 2/5: Starting MCPO on port $MCPO_PORT"
bash scripts/run_mcpo.sh >> "$LOG_FILE" 2>&1 &
if check_server "MCPO" "http://localhost:$MCPO_PORT/openapi.json" 30; then
    echo ""
else
    error "MCPO failed to start. Check $LOG_FILE"
    exit 1
fi

# 3. Web Server (8002)
log "Step 3/5: Starting Web Server on port $WEB_PORT"
bash scripts/run_web.sh >> "$LOG_FILE" 2>&1 &
if check_server "Web Server" "http://localhost:$WEB_PORT/ping" 30; then
    echo ""
else
    error "Web Server failed to start. Check $LOG_FILE"
    exit 1
fi

# 4. n8n (5678) - Docker container
log "Step 4/5: Starting n8n on port $N8N_PORT"
bash docker/run-n8n.sh -p $N8N_PORT >> "$LOG_FILE" 2>&1
if check_container "n8n" 30 && check_server "n8n" "http://localhost:$N8N_PORT/" 30; then
    echo ""
else
    error "n8n failed to start. Check $LOG_FILE and 'docker logs n8n'"
    exit 1
fi

# 5. OpenWebUI (9090) - Docker container
log "Step 5/5: Starting OpenWebUI on port $OPENWEBUI_PORT"
bash docker/run-openwebui.sh -p $OPENWEBUI_PORT >> "$LOG_FILE" 2>&1
if check_container "openwebui" 30 && check_server "OpenWebUI" "http://localhost:$OPENWEBUI_PORT/" 30; then
    echo ""
else
    error "OpenWebUI failed to start. Check $LOG_FILE and 'docker logs openwebui'"
    exit 1
fi

# Success summary
echo ""
echo "================================================================"
success "All servers started successfully!"
echo "================================================================"
echo ""
echo "📊 Server Status:"
echo "  ✓ MCP Server:    http://localhost:$MCP_PORT"
echo "  ✓ MCPO:          http://localhost:$MCPO_PORT (Swagger: /docs)"
echo "  ✓ Web Server:    http://localhost:$WEB_PORT"
echo "  ✓ n8n:           http://localhost:$N8N_PORT"
echo "  ✓ OpenWebUI:     http://localhost:$OPENWEBUI_PORT"
echo ""
echo "📝 Logs:"
echo "  Startup log:     $LOG_FILE"
echo "  MCP:             /tmp/mcp_server.log"
echo "  MCPO:            /tmp/mcpo_server.log"
echo "  Web:             /tmp/web_server.log"
echo "  n8n:             docker logs n8n"
echo "  OpenWebUI:       docker logs openwebui"
echo ""
echo "🛑 To stop all servers: bash scripts/stop_all_servers.sh"
echo "================================================================"
echo ""
