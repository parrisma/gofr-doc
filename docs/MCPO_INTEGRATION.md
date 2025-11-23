# MCPO Integration for doco

MCPO (MCP-to-OpenAPI) wrapper for exposing doco MCP server as OpenAPI endpoints for Open WebUI integration.

## Quick Start - Public Mode (No Authentication)

```bash
# Start MCP server in public mode
python app/main_mcp.py --port=8010 --no-auth

# Start MCPO wrapper (in another terminal)
./scripts/mcpo_wrapper.sh --mode public --mcp-port 8010 --mcpo-port 8011

# Access OpenAPI docs
open http://localhost:8011/docs
```

## Quick Start - Authenticated Mode

```bash
# Start MCP server with authentication
export DOCO_JWT_SECRET="your-secret-key"
python app/main_mcp.py --port=8010

# Generate a JWT token (or use existing one)
export DOCO_JWT_TOKEN="your-jwt-token"

# Start MCPO wrapper with auth
./scripts/mcpo_wrapper.sh --mode auth --jwt-token "$DOCO_JWT_TOKEN"

# Access OpenAPI docs
open http://localhost:8011/docs
```

## Usage Options

### 1. Shell Script Wrapper (Recommended)

```bash
# Public mode
./scripts/mcpo_wrapper.sh

# Authenticated mode
./scripts/mcpo_wrapper.sh --mode auth --jwt-token "your-token"

# Custom ports
./scripts/mcpo_wrapper.sh --mcp-port 8010 --mcpo-port 8011
```

### 2. Python Entry Point

```bash
# Public mode
python app/main_mcpo.py --no-auth

# Authenticated mode
python app/main_mcpo.py --auth --auth-token "your-token"
```

### 3. Direct uv Command

```bash
# Public mode
uv tool run mcpo --port 8011 --api-key "changeme" \
  --server-type "streamable-http" \
  -- http://localhost:8010/mcp

# Authenticated mode
uv tool run mcpo --port 8011 --api-key "changeme" \
  --server-type "streamable-http" \
  --header '{"Authorization": "Bearer YOUR_TOKEN"}' \
  -- http://localhost:8010/mcp
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCO_MCPO_MODE` | Auth mode: `auth` or `public` | `public` |
| `DOCO_MCP_PORT` | MCP server port | `8010` |
| `DOCO_MCPO_PORT` | MCPO proxy port | `8011` |
| `DOCO_MCPO_API_KEY` | API key for Open WebUI → MCPO | `changeme` |
| `DOCO_JWT_TOKEN` | JWT token for MCPO → MCP | (none) |
| `DOCO_MCP_HOST` | MCP server host | `localhost` |

## Integration with Open WebUI

Once MCPO is running, configure Open WebUI to use the OpenAPI endpoint:

1. Open WebUI Settings → Tools → Add OpenAPI Server
2. Enter URL: `http://localhost:8011`
3. Enter API Key: Value of `DOCO_MCPO_API_KEY` (default: `changeme`)
4. Click "Add Server"

The doco tools will now be available in Open WebUI!

## Architecture

```
Open WebUI → MCPO Proxy → doco MCP Server
   (HTTP)     (OpenAPI)      (Streamable HTTP)
              
   Port 3000  Port 8011      Port 8010
```

### Authentication Flow

**Public Mode (No Auth)**:
- Open WebUI → MCPO: API key authentication
- MCPO → MCP: No authentication
- MCP tools: Read-only operations only

**Authenticated Mode**:
- Open WebUI → MCPO: API key authentication
- MCPO → MCPO: JWT Bearer token in headers
- MCP tools: Full access with group-based authorization

## Available Tools

When exposed via MCPO, all doco MCP tools become OpenAPI endpoints:

- `ping` - Health check
- `list_templates` - List available document templates
- `get_template_details` - Get template information
- `create_document_session` - Start new document session
- `add_fragment` - Add fragment to document
- `set_global_parameters` - Set document parameters
- `get_document` - Render and retrieve document
- `abort_document_session` - Cancel document session
- `list_styles` - List available styles
- And more...

## Configuration File Support

Create `config/mcpo_config.json` for advanced configuration:

```json
{
  "mcpServers": {
    "doco": {
      "type": "streamable-http",
      "url": "http://localhost:8010/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
```

Run with config file:
```bash
uv tool run mcpo --config config/mcpo_config.json --port 8011
```

## Troubleshooting

### MCPO not found
```bash
# Install mcpo via uv
uv add mcpo
# Or use uv tool run (recommended)
uv tool run mcpo --version
```

### Connection refused
- Check MCP server is running: `lsof -i :8010`
- Verify MCP endpoint: `curl http://localhost:8010/mcp`

### Authentication errors
- Verify JWT token is valid and not expired
- Check token has correct group claim
- Ensure `DOCO_JWT_SECRET` matches between MCP server and token generation

### Port already in use
```bash
# Kill process on MCPO port
fuser -k 8000/tcp

# Kill process on MCP port
fuser -k 8011/tcp
```

## Development

The MCPO wrapper is implemented in `app/mcpo/`:

- `__init__.py` - Module initialization
- `wrapper.py` - Core wrapper implementation
- `config.py` - Configuration file management

Main entry points:
- `app/main_mcpo.py` - Python entry point
- `scripts/mcpo_wrapper.sh` - Shell script wrapper

## See Also

- [MCPO GitHub Repository](https://github.com/open-webui/mcpo)
- [Open WebUI Documentation](https://docs.openwebui.com/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
