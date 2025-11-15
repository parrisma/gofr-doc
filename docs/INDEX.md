# Documentation Index

Complete guide to doco documentation organized by topic.

## 🚀 Getting Started

- **[README.md](../README.md)** — Project overview, installation, quick start
- **[PROJECT_SPEC.md](../PROJECT_SPEC.md)** — Technical specification and design decisions
- **[DOCUMENT_GENERATION.md](DOCUMENT_GENERATION.md)** — Workflow guide and API reference

## 📋 Core Guides

| Guide | Purpose |
|-------|---------|
| [DOCUMENT_GENERATION.md](DOCUMENT_GENERATION.md) | Document generation workflow, tool reference, examples |
| [DATA_PERSISTENCE.md](DATA_PERSISTENCE.md) | Session storage, persistence across restarts, backup/recovery |
| [AUTHENTICATION.md](AUTHENTICATION.md) | JWT tokens, authentication setup, token management |

## 🐳 Infrastructure & Deployment

| Guide | Purpose |
|-------|---------|
| [DOCKER.md](DOCKER.md) | Docker setup for dev and production, image building, volume management |

## 🔗 Integration

| Guide | Purpose |
|-------|---------|
| [N8N_MCP_SETUP.md](N8N_MCP_SETUP.md) | n8n integration setup |
| [N8N_INTEGRATION.md](N8N_INTEGRATION.md) | n8n workflow examples |
| [README_N8N_MCP.md](README_N8N_MCP.md) | n8n MCP client configuration |
| [N8N_TROUBLESHOOTING.md](N8N_TROUBLESHOOTING.md) | n8n integration troubleshooting |

## 📖 Architecture Overview

### Application Structure

```
app/
├── auth/              # JWT services and middleware
├── config.py          # Runtime configuration
├── logger/            # Structured logging
├── mcp_server.py      # MCP tool handlers
├── rendering/         # HTML → PDF/Markdown conversion
├── sessions/          # Session manager and persistence
├── storage/           # File-system storage backends
├── styles/            # Style registry and CSS
├── templates/         # Template registry and rendering
├── validation/        # Pydantic models and validators
└── web_server.py      # FastAPI application factory
```

### Key Components

1. **Template System** (`app/templates/`)
   - YAML metadata defining parameters and fragments
   - Jinja2 templates for HTML generation
   - Fragment composition within documents

2. **Style System** (`app/styles/`)
   - CSS bundles decoupled from templates
   - Applied uniformly across HTML, PDF, Markdown
   - Style registry with metadata

3. **Session Management** (`app/sessions/`)
   - Stateful document assembly
   - Fragment ordering and persistence
   - Global parameter tracking

4. **Rendering Engine** (`app/rendering/`)
   - HTML generation from templates
   - WeasyPrint for PDF conversion
   - html2text for Markdown conversion

5. **Validation Layer** (`app/validation/`)
   - Pydantic schemas for all MCP inputs/outputs
   - Type-safe parameter validation
   - Helpful error messages with recovery strategies

## 🛠️ Development

### Running Tests

```bash
# Full test suite
pytest test/

# Specific test module
pytest test/styles/
pytest test/mcp/
pytest test/web/

# With coverage
pytest test/ --cov=app --cov-report=html
```

### VS Code Development

1. **Launch Configurations** — `.vscode/launch.json` includes targets for:
   - Style Tests
   - Storage Tests
   - Auth Tests
   - All Tests
   - Current file execution

2. **Debugging** — Attach debugger to MCP or web server via launch config

3. **Remote Development** — Use Dev Containers for isolated Python environment

## 📡 API Reference

### MCP Tools

13 tools organized by purpose:

**Discovery** (read-only):
- `list_templates`
- `get_template_details`
- `list_template_fragments`
- `get_fragment_details`
- `list_styles`

**Session Lifecycle**:
- `create_document_session`
- `set_global_parameters`
- `abort_document_session`

**Fragment Management**:
- `add_fragment`
- `remove_fragment`
- `list_session_fragments`

**Rendering**:
- `get_document`

See [DOCUMENT_GENERATION.md](DOCUMENT_GENERATION.md) for detailed request/response examples.

## 🔐 Security

- JWT-based authentication shared across web and MCP transports
- Token storage isolated from rendered documents
- Per-session data isolation via UUIDs
- File-level access control through Unix permissions

See [AUTHENTICATION.md](AUTHENTICATION.md) for setup and token management.

## 🚢 Deployment

### Quick Start

```bash
# Development
./docker/run-dev.sh

# Production
./docker/run-prod.sh [WEB_PORT] [MCP_PORT]
```

See [DOCKER.md](DOCKER.md) for detailed Docker setup and troubleshooting.

### Persistent Data

- **Development**: Automatic via mounted project directory
- **Production**: Mount `~/doco_data` for session persistence

See [DATA_PERSISTENCE.md](DATA_PERSISTENCE.md) for backup/recovery procedures.

## 📝 Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DOCO_JWT_SECRET` | auto-generated | JWT signing secret |
| `DOCO_DATA_DIR` | `{project}/data` | Data directory location |
| `WEB_HOST` | `0.0.0.0` | Web server listen address |
| `MCP_HOST` | `0.0.0.0` | MCP server listen address |

### CLI Flags

- `--host` — Override listen address
- `--port` — Override listen port
- `--require-auth` / `--no-auth` — Enable/disable authentication
- `--jwt-secret` — Override JWT secret

## 🐛 Troubleshooting

### Common Issues

| Issue | Guide |
|-------|-------|
| Session not persisting | [DATA_PERSISTENCE.md](DATA_PERSISTENCE.md) |
| Authentication failures | [AUTHENTICATION.md](AUTHENTICATION.md) |
| Docker build errors | [DOCKER.md](DOCKER.md) |
| n8n integration problems | [N8N_TROUBLESHOOTING.md](N8N_TROUBLESHOOTING.md) |
| PDF rendering issues | [DOCKER.md](DOCKER.md) — WeasyPrint dependencies |

## 📚 Additional Resources

- **[PROJECT_SPEC.md](../PROJECT_SPEC.md)** — Full technical specification with design rationale
- **[requirements.txt](../requirements.txt)** — Minimal dependency list with versions
- **[pyproject.toml](../pyproject.toml)** — Full dependency and tool configuration

## 🔄 Document Update History

| Date | Change | File(s) |
|------|--------|---------|
| Nov 15, 2025 | Migrated from graph rendering to document generation | README.md, DOCKER.md, DATA_PERSISTENCE.md |
| Nov 15, 2025 | Created comprehensive document generation guide | DOCUMENT_GENERATION.md |
| Nov 13, 2025 | Finalized project specification | PROJECT_SPEC.md |

---

**Questions?** Start with [README.md](../README.md) or [DOCUMENT_GENERATION.md](DOCUMENT_GENERATION.md) for common workflows.
