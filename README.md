# doco - Document Generation MCP Service

doco delivers a stateful, discoverable document generation API exposed to agentic LLM clients via the Model Context Protocol (MCP). The service combines a FastAPI web interface and a Streamable HTTP MCP server backed by Pydantic schemas, Jinja2 templating, reusable styles, and multi-format rendering (HTML, PDF, Markdown).

## Features

- **Template-driven document generation**: Type-safe parameters, flexible Jinja2 rendering, modular fragment assembly
- **Multi-format output**: HTML (canonical), PDF (WeasyPrint), Markdown (html2text)
- **Dual interface**: REST API on port 8010 and MCP Streamable HTTP endpoint on port 8011
- **Stateful sessions**: Persistent across restarts; supports iterative fragment assembly and re-rendering
- **Reusable styles**: Decoupled CSS bundles applied uniformly across output formats
- **Optional JWT authentication**: Shared between web and MCP transports
- **Structured session logging**: Per-request correlation and detailed diagnostics

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd doco

# Install dependencies with uv
uv sync

# Or install core packages manually
uv pip install fastapi uvicorn httpx mcp pydantic jinja2 weasyprint html2text pyyaml
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
# Create a document session
curl -X POST http://localhost:8010/session \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"template_id": "basic_report"}'

# Set global parameters
curl -X POST http://localhost:8010/session/{session_id}/parameters \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"title": "Q4 Report", "author": "Data Team"}'

# Add fragments
curl -X POST http://localhost:8010/session/{session_id}/fragment \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"fragment_id": "paragraph", "parameters": {"text": "Introduction..."}}'

# Render document
curl -X GET "http://localhost:8010/session/{session_id}/render?format=pdf&style_id=default" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -o document.pdf
```

### MCP Server

Use any MCP-compatible client to call document generation tools:

- `list_templates` — discover available templates
- `get_template_details` — fetch template metadata and parameter schemas
- `list_template_fragments` — list available fragments within a template
- `get_fragment_details` — retrieve fragment parameter schema
- `list_styles` — discover available rendering styles
- `create_document_session` — start a new document session
- `set_global_parameters` — configure session-wide parameters
- `add_fragment` — insert a fragment with parameters
- `remove_fragment` — delete a fragment instance
- `list_session_fragments` — inspect ordered fragments in a session
- `abort_document_session` — discard session and cleanup storage
- `get_document` — render session in requested format (html, pdf, md)

See [docs/DOCUMENT_GENERATION.md](docs/DOCUMENT_GENERATION.md) for detailed workflow examples.

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
│   ├── rendering/           # Rendering engine (HTML → PDF/Markdown)
│   ├── sessions/            # Session manager and persistence
│   ├── storage/             # File-system storage backends
│   ├── styles/              # Style registry (CSS bundles)
│   ├── templates/           # Template registry (YAML + Jinja2)
│   ├── validation/          # Pydantic schemas and validators
│   └── web_server.py        # FastAPI application factory
├── data/
│   ├── auth/                # Default token storage
│   └── storage/             # Session and document storage
├── docker/                  # Container build/run scripts
├── docs/                    # Documentation suite
├── scripts/                 # Utility scripts (token/storage managers)
├── styles/                  # Static style bundles (CSS)
├── templates/               # Static template bundles (YAML + Jinja2)
├── test/                    # Pytest suites
├── pyproject.toml           # Dependency and tool configuration
├── requirements.txt         # Minimal dependency pin list
└── README.md                # This file
```

## Documentation

📚 **[Documentation Index](docs/INDEX.md)** — master list of all guides and references.

- **Core guides**: [DOCUMENT_GENERATION.md](docs/DOCUMENT_GENERATION.md), [DATA_PERSISTENCE.md](docs/DATA_PERSISTENCE.md)
- **Authentication**: [AUTHENTICATION.md](docs/AUTHENTICATION.md)
- **Infrastructure**: [DOCKER.md](docs/DOCKER.md)
- **n8n integration**: [README_N8N_MCP.md](docs/README_N8N_MCP.md), [N8N_MCP_SETUP.md](docs/N8N_MCP_SETUP.md), [N8N_TROUBLESHOOTING.md](docs/N8N_TROUBLESHOOTING.md)

## Architecture Overview

- **FastAPI Web Server** (`app/web_server.py`): REST endpoints for session lifecycle and rendering
- **MCP Server** (`app/mcp_server.py`): Document tools over Streamable HTTP
- **Template Registry** (`app/templates/`): YAML metadata + Jinja2 templates
- **Style Registry** (`app/styles/`): CSS bundles decoupled from templates
- **Rendering Engine** (`app/rendering/engine.py`): HTML generation → PDF/Markdown conversion
- **Session Manager** (`app/sessions/`): Lifecycle, fragment assembly, persistence
- **Validation Layer** (`app/validation/`): Pydantic schemas enforcing document constraints
- **Auth & Logging** (`app/auth/`, `app/logger/`): Shared JWT and structured logging

## Development

```bash
# Run full test suite
uv run pytest

# Run only style tests
uv run pytest test/styles

# Run MCP tests
uv run pytest test/mcp

# Run web-layer tests
uv run pytest test/web
```

Launch configurations for VS Code debugging are provided in `.vscode/launch.json`.

## License

MIT License — see [LICENSE](LICENSE) for details.


