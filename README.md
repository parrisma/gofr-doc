# doco - Graph Rendering Service

doco delivers programmable chart rendering over both HTTP and the Model Context Protocol (MCP). The service combines a FastAPI REST interface (complete with generated OpenAPI documentation) and a Streamable HTTP MCP server backed by matplotlib, reusable templates, and theme customization.

## Features

- Multiple chart types: line, scatter, bar, and multi-dataset layouts
- Dual interface: REST API on port 8010 and MCP Streamable HTTP endpoint on port 8011
- Extensible rendering engine with template, theme, and style registries
- Optional JWT authentication shared between web and MCP transports
- Flexible output targets: PNG, JPG, SVG, PDF, and disk-backed proxy mode
- Advanced controls for axes, ticks, annotations, transparency, and styling
- Structured session logging with per-request correlation

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd doco

# Install dependencies with uv
uv sync

# Or install the core packages manually
uv pip install matplotlib fastapi uvicorn httpx mcp pydantic
```

### Running the Web Server

```bash
# Set JWT secret (required when authentication is enabled)
export DOCO_JWT_SECRET="your-secure-secret-key"

# Launch the FastAPI server
python -m app.main_web

# REST API: http://localhost:8010
# OpenAPI docs: http://localhost:8010/docs
```

### Running the MCP Server

```bash
# Uses the same DOCO_JWT_SECRET when auth is enabled
python -m app.main_mcp

# MCP Streamable HTTP endpoint: http://localhost:8011/mcp/
```

### Create Authentication Tokens

```bash
# Create a JWT token for a group
python3 scripts/token_manager.py create --group mygroup --expires 30

# List existing tokens
python3 scripts/token_manager.py list
```

See [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md) for the full JWT configuration guide.

## Usage Examples

### REST API (FastAPI)

```bash
curl -X POST http://localhost:8010/render \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "title": "Sales Data",
    "x": [1, 2, 3, 4, 5],
    "y1": [10, 25, 18, 30, 42],
    "xlabel": "Month",
    "ylabel": "Sales",
    "type": "line",
    "theme": "dark",
    "return_base64": false
  }' -o chart.png
```

### MCP Server

Use any MCP-compatible client (including n8n's MCP Client Tool) to call the `render_graph` tool exposed at `http://localhost:8011/mcp/`. Sample event payloads and workflows are documented in [docs/README_N8N_MCP.md](docs/README_N8N_MCP.md).

## Configuration

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `DOCO_JWT_SECRET` | auto-generated (web) / required for auth | Shared JWT secret used by both servers when authentication is enabled |
| `DOCO_DATA_DIR` | `<repo>/data` | Base directory for auth and storage data |
| `WEB_HOST` | `0.0.0.0` | Host interface for web server (via CLI flags) |
| `MCP_HOST` | `0.0.0.0` | Host interface for MCP server (via CLI flags) |

CLI flags in `app/main_web.py` and `app/main_mcp.py` allow overriding host, port, auth, and logging behaviour at runtime.

## Project Structure

```text
doco/
├── app/
│   ├── auth/                # JWT services and middleware
│   ├── config.py            # Runtime configuration helpers
│   ├── logger/              # Structured logging adapters
│   ├── main_mcp.py          # MCP server entry point
│   ├── main_web.py          # Web server entry point
│   ├── mcp_server.py        # MCP tool wiring
│   ├── rendering/           # Rendering engine and helpers
│   ├── sessions/            # Session manager and persistence utilities
│   ├── storage/             # File-system storage backends
│   ├── styles/              # Matplotlib style registry
│   ├── templates/           # Graph template registry
│   ├── themes/              # Theme definitions
│   ├── validation/          # Pydantic models and validators
│   └── web_server.py        # FastAPI application factory
├── data/
│   ├── auth/                # Default token storage
│   └── storage/             # Proxy-mode image storage
├── docker/                  # Container build/run scripts and Dockerfiles
├── docs/                    # Documentation suite
├── scripts/                 # Utility scripts (token/storage managers)
├── test/                    # Pytest suites (web, MCP, auth, validation, storage)
├── pyproject.toml           # Dependency and tool configuration
├── requirements.txt         # Minimal dependency pin list
└── README.md                # This file
```

## Documentation

📚 **[Documentation Index](docs/INDEX.md)** — master list of all guides and references.

- Core guides: [MCP_README](docs/MCP_README.md), [PROXY_MODE](docs/PROXY_MODE.md), [DATA_PERSISTENCE](docs/DATA_PERSISTENCE.md)
- Authentication: [AUTHENTICATION](docs/AUTHENTICATION.md)
- Infrastructure: [DOCKER](docs/DOCKER.md), [SCRIPTS](docs/SCRIPTS.md), [VSCODE_LAUNCH_CONFIGURATIONS](docs/VSCODE_LAUNCH_CONFIGURATIONS.md)
- Rendering internals: [RENDER](docs/RENDER.md), [STORAGE](docs/STORAGE.md), [THEMES](docs/THEMES.md), [LOGGER](docs/LOGGER.md)
- Testing playbooks: [TEST_MCP](docs/TEST_MCP.md), [TEST_WEB](docs/TEST_WEB.md), [TEST_AUTH](docs/TEST_AUTH.md), [TEST_COVERAGE_MULTI_DATASET](docs/TEST_COVERAGE_MULTI_DATASET.md)
- n8n integration: [README_N8N_MCP](docs/README_N8N_MCP.md), [N8N_MCP_SETUP](docs/N8N_MCP_SETUP.md), [N8N_TROUBLESHOOTING](docs/N8N_TROUBLESHOOTING.md)

## Architecture Overview

- **FastAPI Web Server** (`app/web_server.py`): Serves REST endpoints, health checks, and proxy downloads
- **MCP Server** (`app/mcp_server.py`): Provides the `render_graph` tool over Streamable HTTP
- **Rendering Engine** (`app/rendering/engine.py`): Coordinates matplotlib plotting, templates, styles, and themes
- **Session & Storage Layers** (`app/sessions/`, `app/storage/`): Manage request state and persisted artifacts
- **Validation Layer** (`app/validation/`): Pydantic models and cross-field validators enforcing graph constraints
- **Auth & Logging** (`app/auth/`, `app/logger/`): Shared JWT handling and structured logging utilities

## Development

```bash
# Run full test suite
uv run pytest

# Run only MCP tests
uv run pytest test/mcp

# Run web-layer tests
uv run pytest test/web
```

Launch configurations for VS Code debugging the web and MCP servers are provided in `.vscode/launch.json`.

## License

MIT License — see [LICENSE](LICENSE) for details.

