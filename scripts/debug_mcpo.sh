#!/bin/bash
# Debug MCPO startup issues

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

MCP_PORT=8010
MCPO_PORT=8011
MCP_URL="http://localhost:$MCP_PORT/mcp"

echo "=== MCPO Debug Script ==="
echo ""

# Check if MCP server is running
echo "1. Checking MCP server at $MCP_URL..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$MCP_PORT/ 2>/dev/null)
echo "   HTTP response: $HTTP_CODE"
if [[ "$HTTP_CODE" =~ ^(200|404|405)$ ]]; then
    echo "   ✓ MCP server is responding"
else
    echo "   ✗ MCP server is NOT responding"
    echo "   Start it with: scripts/run_mcp.sh"
    exit 1
fi
echo ""

# Check if mcpo tool is available
echo "2. Checking mcpo tool availability..."
if uv tool list | grep -q "mcpo"; then
    echo "   ✓ mcpo is installed via uv tool"
else
    echo "   ⚠ mcpo not in uv tool list, will be installed on first run"
fi
echo ""

# Build and display the exact command
echo "3. MCPO command that will be executed:"
CMD="uv tool run mcpo --port $MCPO_PORT --server-type streamable-http -- $MCP_URL"
echo "   $CMD"
echo ""

# Try running MCPO in foreground to see errors
echo "4. Running MCPO in foreground (Ctrl+C to stop)..."
echo "   Logs will appear below:"
echo "   ===================="
echo ""

$CMD

