# gofr-doc - Document Generation MCP Service

gofr-doc delivers a stateful, discoverable document generation API exposed to agentic LLM clients via the Model Context Protocol (MCP). The service combines a FastAPI web interface and a Streamable HTTP MCP server backed by Pydantic schemas, Jinja2 templating, reusable styles, and multi-format rendering (HTML, PDF, Markdown).

## Features

- **Template-driven document generation**: Type-safe parameters, flexible Jinja2 rendering, modular fragment assembly
- **Rich table fragments**: 14 parameters including number formatting (currency, percent), alignment, sorting, colors, column widths
- **Multi-format output**: HTML (canonical), PDF (WeasyPrint), Markdown (html2text with alignment markers)
- **Dual interface**: REST API on port 8010 and MCP Streamable HTTP endpoint on port 8011
- **Stateful sessions**: Persistent across restarts; supports iterative fragment assembly and re-rendering
- **Reusable styles**: Decoupled CSS bundles applied uniformly across output formats
- **Group-based security**: Optional JWT authentication with multi-tenant isolation
- **Session isolation**: Group-based access control prevents cross-tenant data access
- **Structured session logging**: Per-request correlation and detailed diagnostics
- **Proxy mode rendering**: Store rendered documents server-side for later retrieval

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd doco

# Install dependencies with uv
uv sync

# Or install core packages manually
uv pip install fastapi uvicorn httpx mcp pydantic jinja2 weasyprint html2text pyyaml babel
```

## 📚 Documentation

### Quick Start Summary

| Guide | Description |
|-------|-------------|
| **[Development Guide](docs/DEVELOPMENT.md)** | Complete developer onboarding, setup, and testing |
| **[Document Generation](docs/DOCUMENT_GENERATION.md)** | Core workflow: sessions → fragments → rendering |
| **[Project Specification](docs/PROJECT_SPEC.md)** | Architecture, design decisions, and technical details |
| **[Configuration](app/config_docs.py)** | Environment variables (`python app/config_docs.py`) |

### Core Documentation

| Guide | Description |
|-------|-------------|
| **[Authentication & Security](docs/AUTHENTICATION.md)** | JWT tokens, groups, multi-tenancy, security best practices |
| **[Features Guide](docs/FEATURES.md)** | Tables, images, groups, proxy mode - comprehensive reference |
| **[Integration Guide](docs/INTEGRATIONS.md)** | n8n setup, HTTP API, MCP protocol, troubleshooting |
| **[Docker Deployment](docs/DOCKER.md)** | Container setup, docker-compose, production deployment |
| **[Data Persistence](docs/DATA_PERSISTENCE.md)** | Session storage, recovery, file management |

> 💡 **Pro Tip**: Start with [DEVELOPMENT.md](docs/DEVELOPMENT.md) for complete setup, then explore [FEATURES.md](docs/FEATURES.md) for all capabilities.

### Running Without Authentication (Development)

```bash
# Launch the FastAPI server (no authentication)
python -m app.main_web

# Launch the MCP server (no authentication)
python -m app.main_mcp

# All sessions operate in the "public" group
# REST API: http://localhost:8010
# MCP endpoint: http://localhost:8011/mcp/
# OpenAPI docs: http://localhost:8010/docs
```

### Running With Authentication (Production)

```bash
# Set JWT secret (required for authentication)
export DOCO_JWT_SECRET="your-secure-secret-key"
export DOCO_TOKEN_STORE="/path/to/token_store.json"

# Launch servers with authentication
python -m app.main_web --jwt-secret "$DOCO_JWT_SECRET" --token-store "$DOCO_TOKEN_STORE"
python -m app.main_mcp --jwt-secret "$DOCO_JWT_SECRET" --token-store "$DOCO_TOKEN_STORE"

# Or use convenience scripts for testing
bash scripts/run_web_auth.sh
bash scripts/run_mcp_auth.sh
```

### Token Management

```bash
# Create a JWT token for a group
./scripts/token_manager.sh create --group engineering --expires 30

# List all active tokens
./scripts/token_manager.sh list

# Revoke a token
./scripts/token_manager.sh revoke --token <token>

# View token details
./scripts/token_manager.sh verify --token <token>
```

**Security Note**: When authentication is enabled:

- Sessions are bound to the group in the JWT token
- Each group's sessions are isolated (multi-tenant)
- Cross-group access attempts return generic "SESSION_NOT_FOUND" errors
- Discovery tools (list_templates, list_styles) do not require authentication

See [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md) for the full JWT configuration guide.

## Usage Examples

### REST API (FastAPI)

```bash
# Create a document session with a friendly alias
curl -X POST http://localhost:8010/session \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"template_id": "basic_report", "alias": "q4-report"}'

# Use the alias in subsequent calls instead of the session UUID
SESSION="q4-report"  # or use the returned session_id UUID

# Set global parameters (using alias)
curl -X POST http://localhost:8010/session/$SESSION/parameters \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"title": "Q4 Report", "author": "Data Team"}'

# Add fragments (using alias)
curl -X POST http://localhost:8010/session/$SESSION/fragment \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"fragment_id": "paragraph", "parameters": {"text": "Introduction..."}}'

# Render document (using alias)
curl -X GET "http://localhost:8010/session/$SESSION/render?format=pdf&style_id=default" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -o document.pdf
```

**💡 Tip**: Use memorable aliases like `q4-report`, `invoice-march`, or `weekly-summary` instead of UUIDs. Aliases work everywhere session_id is accepted!

### MCP Server

Use any MCP-compatible client to call document generation tools:

**Discovery Tools** (no authentication required):

- `ping` — health check and service status
- `help` — comprehensive workflow documentation and guidance
- `list_templates` — discover available templates
- `get_template_details` — fetch template metadata and parameter schemas
- `list_template_fragments` — list available fragments within a template
- `get_fragment_details` — retrieve fragment parameter schema
- `list_styles` — discover available rendering styles

**Session Tools** (authentication required when enabled):

- `create_document_session` — start a new document session with a friendly alias (bound to authenticated group)
- `list_active_sessions` — discover all sessions in your group with their aliases
- `set_global_parameters` — configure session-wide parameters (accepts alias or UUID)
- `add_fragment` — insert a fragment with parameters (accepts alias or UUID)
- `add_image_fragment` — insert an image with URL (accepts alias or UUID)
- `remove_fragment` — delete a fragment instance (accepts alias or UUID)
- `list_session_fragments` — inspect ordered fragments in a session (accepts alias or UUID)
- `get_session_status` — get current session state and readiness (accepts alias or UUID)
- `validate_parameters` — pre-validate parameters before saving
- `abort_document_session` — discard session and cleanup storage (accepts alias or UUID)
- `get_document` — render session in requested format (accepts alias or UUID)

**💡 Session Aliases**: Every session requires a friendly alias (3-64 chars: alphanumeric, hyphens, underscores). Use memorable names like `invoice-march` or `weekly-report` instead of UUIDs. All session tools accept either the alias or UUID for identification.

**Authentication Flow**:

1. Client sends JWT token in `Authorization: Bearer <token>` header
2. Server extracts group claim from token
3. Session is tagged with the authenticated group
4. All subsequent operations verify `session.group == caller.group`
5. Cross-group access attempts are denied with generic errors

See [docs/DOCUMENT_GENERATION.md](docs/DOCUMENT_GENERATION.md) for detailed workflow examples.

## Table Fragment

The table fragment provides rich, formatted tables with 14 configurable parameters:

**Core Features**:

- Number formatting (currency, percent, decimal, integer, accounting)
- Column alignment (left, center, right)
- Sorting (single or multi-column, ascending/descending)
- Visual styling (borders, zebra striping, compact mode)
- Colors and highlighting (header, rows, columns with theme colors or hex codes)
- Column width control (percentages or pixels)

**Quick Example**:

```python
{
    "fragment_id": "quarterly_results",
    "parameters": {
        "rows": [
            ["Quarter", "Revenue", "Growth"],
            ["Q1 2024", "1250000", "0.15"],
            ["Q2 2024", "1380000", "0.104"]
        ],
        "has_header": True,
        "title": "Financial Performance",
        "column_alignments": ["left", "right", "right"],
        "number_format": {
            "1": "currency:USD",
            "2": "percent"
        },
        "header_color": "primary",
        "zebra_stripe": True,
        "sort_by": {"column": "Revenue", "order": "desc"}
    }
}
```

**Output Formats**:

- HTML/PDF: Full feature support (colors, borders, styling)
- Markdown: Table structure with alignment markers (colors omitted)

See [Features Guide](docs/FEATURES.md#tables) for complete documentation with examples.

## Configuration

### Environment Variables

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `GOFR_DOC_JWT_SECRET` | None (auth disabled) | Shared JWT secret for both servers. When set, enables authentication and group-based isolation |
| `GOFR_DOC_TOKEN_STORE` | `<data_dir>/auth/tokens.json` | Path to token store file for token management |
| `GOFR_DOC_DATA_DIR` | `<repo>/data` | Base directory for auth, storage, sessions, and proxy documents |
| `GOFR_DOC_MCP_PORT` | `8010` | Port for MCP server (used by tests) |
| `GOFR_DOC_WEB_PORT` | `8012` | Port for web server (used by tests) |

### CLI Options

Both `app/main_web.py` and `app/main_mcp.py` support:

```bash
python -m app.main_web \
  --host 0.0.0.0 \
  --port 8010 \
  --jwt-secret "your-secret" \
  --token-store "/path/to/tokens.json" \
  --templates-dir "./templates" \
  --styles-dir "./styles"
```

### Security Modes

**No Authentication** (default):

- All sessions operate in `"public"` group
- No access control between sessions
- Suitable for single-user development

**With Authentication**:

- Sessions bound to JWT token group claim
- Multi-tenant isolation enforced
- Group-based directory structure: `data/docs/{templates,styles,sessions}/{group}/`
- Cross-group access denied with generic errors

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

## Additional Resources

- **Core guides**: [DOCUMENT_GENERATION.md](docs/DOCUMENT_GENERATION.md), [DATA_PERSISTENCE.md](docs/DATA_PERSISTENCE.md)
- **Authentication**: [AUTHENTICATION.md](docs/AUTHENTICATION.md)
- **Features**: [FEATURES.md](docs/FEATURES.md)
- **Infrastructure**: [DOCKER.md](docs/DOCKER.md)
- **Integration**: [INTEGRATIONS.md](docs/INTEGRATIONS.md)

## Architecture Overview

- **FastAPI Web Server** (`app/web_server.py`): REST endpoints for session lifecycle and rendering
- **MCP Server** (`app/mcp_server.py`): Document tools over Streamable HTTP with group-based security
- **Authentication Service** (`app/auth/`): JWT token management, verification, and group extraction
- **Template Registry** (`app/templates/`): YAML metadata + Jinja2 templates with group isolation
- **Style Registry** (`app/styles/`): CSS bundles decoupled from templates
- **Rendering Engine** (`app/rendering/engine.py`): HTML generation → PDF/Markdown conversion
- **Session Manager** (`app/sessions/`): Lifecycle, fragment assembly, persistence with group boundaries
- **Storage Layer** (`app/storage/`): File-system storage with group-based directory isolation
- **Validation Layer** (`app/validation/`): Pydantic schemas enforcing document constraints
- **Logging** (`app/logger/`): Structured logging with session correlation

### Security Architecture

```
JWT Token → AuthService.verify_token() → TokenInfo.group
                                              ↓
                                    handle_call_tool() injects group
                                              ↓
                            Tool handlers verify session.group == caller.group
                                              ↓
                        Directory isolation: data/docs/{resource}/{group}/
```

**Key Security Features**:

- JWT tokens contain `{"group": "...", "exp": ..., "iat": ...}` claims
- Sessions are bound to the authenticated group during creation
- All session operations verify group ownership before access
- Generic "SESSION_NOT_FOUND" errors prevent information leakage
- Discovery tools bypass authentication for public access

## Development

### Running Tests

```bash
# Run full test suite (300+ tests)
uv run pytest

# Run specific test categories
uv run pytest test/mcp                # MCP server tests
uv run pytest test/web                # Web API tests
uv run pytest test/workflow           # End-to-end workflow tests
uv run pytest test/auth               # Authentication tests
uv run pytest test/storage            # Storage layer tests

# Run security tests
uv run pytest test/mcp/test_mcp_group_security.py -v

# Run with coverage
uv run pytest --cov=app --cov-report=html
```

### Test Server Management

```bash
# Start test servers with authentication
bash scripts/run_mcp_auth.sh    # MCP server on port 8011
bash scripts/run_web_auth.sh    # Web server on port 8010

# Stop test servers
pkill -f "python -m app.main_mcp"
pkill -f "python -m app.main_web"
```

### VS Code Integration

Launch configurations are provided in `.vscode/launch.json`:

- **MCP Server (Dev - No Auth)**: Development without authentication
- **MCP Server (Test - With Auth)**: Testing with JWT authentication
- **Web Server (Dev - No Auth)**: Development without authentication  
- **Web Server (Test - With Auth)**: Testing with JWT authentication
- **MCP Server (Production - With Auth)**: Production configuration

### Test Coverage

The test suite includes:

- **Unit tests**: Core functionality and business logic
- **Integration tests**: MCP/Web server endpoints
- **Security tests**: Group isolation and access control (5 comprehensive tests)
- **Workflow tests**: End-to-end document generation scenarios
- **Concurrency tests**: Session persistence and race conditions

**Current Status**: ✅ 300/300 tests passing

## License

MIT License — see [LICENSE](LICENSE) for details.
