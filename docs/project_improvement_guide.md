# Project Improvement Guide - Key Points for LLM Planning

## Architecture & Design

- **MCP Protocol Integration**: FastAPI + MCP Streamable HTTP with dual interface (REST + MCP tools)
- **Stateful Sessions**: Persistent across restarts with UUID4 identifiers
- **Multi-Tenant Security**: JWT tokens with group claims, session ownership verification, directory isolation
- **Template System**: Pydantic schemas + Jinja2 rendering + YAML metadata
- **Registry Pattern**: BaseRegistry abstract class → TemplateRegistry + StyleRegistry (DRY principle)
- **Rendering Pipeline**: HTML canonical → WeasyPrint PDF → html2text Markdown
- **Storage Layer**: File-based with group-scoped prefixes (`session:<group>:<uuid>`)
- **Validation**: Pydantic v2 throughout with structured error responses

## Code Quality Practices

- **Async-First**: All I/O operations use async/await patterns
- **Type Safety**: Full type hints, Pydantic models, strict validation
- **Error Handling**: Structured ErrorResponse with recovery strategies, no information leakage
- **Logging**: Correlation IDs, structured context, per-request tracing
- **Testing**: 300+ tests including unit, integration, security, workflow, concurrency
- **Documentation**: Inline comments for complex logic, comprehensive markdown docs
- **Configuration**: 12-factor app pattern (env vars > CLI args > defaults)

## Project Structure Patterns

```
app/
  {domain}/          # Feature modules (auth, sessions, rendering, etc.)
    __init__.py      # Public API exports
    {service}.py     # Business logic
    {models}.py      # Data models (optional)
  main_{server}.py   # Server entry points
  {domain}_server.py # Server implementations
  config.py          # Runtime configuration
  registry_base.py   # Shared base classes
```

## Testing Strategy

- **Test Organization**: Mirror app/ structure in test/
- **Fixtures**: Centralized in conftest.py with session/function scopes
- **Server Testing**: Use `--with-servers` flag to start MCP/Web servers for integration tests
- **Security Testing**: Verify group isolation, access denial, information leakage prevention
- **Workflow Testing**: End-to-end scenarios (create → configure → render → cleanup)
- **Coverage Target**: Core business logic 80%+, critical paths 100%

## Server Management

- **Individual Scripts**: `run_{server}.sh` for single server startup with health checks
- **Orchestration Scripts**: `start_all_servers.sh` sequential startup with verification
- **Stop Scripts**: `stop_all_servers.sh` with 100% termination verification (SIGTERM → SIGKILL)
- **Docker Containers**: Separate run scripts in docker/ for n8n, OpenWebUI
- **Health Checks**: curl-based readiness probes with retry logic and timeouts
- **Port Management**: Verify ports free after shutdown, handle stuck processes

## Launch Configuration

- **VS Code Integration**: .vscode/launch.json with organized configurations
- **Configuration Groups**: Tests (with/without servers) → Dev (with/without auth) → Production → Tools
- **Debugger Support**: debugpy for Python, node-terminal for bash scripts
- **Environment Variables**: Production uses env vars, dev uses inline test values
- **Port Separation**: Dev ports differ from Production (MCP=8010, MCPO=8011, WEB=8012)

## Documentation Strategy

- **Consolidated Structure**: Avoid duplication, cross-reference related docs
- **Index File**: Central navigation with document summaries
- **Document Types**: 
  - project_spec.md: Architecture and design decisions
  - {FEATURE}.md: Feature-specific guides with examples
  - {INTEGRATION}.md: External system setup and troubleshooting
  - development.md: Developer onboarding and workflows
- **Code Comments**: Explain "why" not "what", reference decisions, note trade-offs
- **API Documentation**: OpenAPI/Swagger for REST, tool descriptions for MCP

## Security Principles

- **Group-Based Multi-Tenancy**: Sessions bound to JWT group claim
- **Ownership Verification**: All session operations check `session.group == caller.group`
- **Information Hiding**: Generic errors (SESSION_NOT_FOUND) prevent enumeration
- **Directory Isolation**: Group-scoped paths for storage, sessions, documents
- **No-Auth Mode**: Development default with "public" group
- **Token Management**: Separate token_manager.py script for lifecycle operations
- **Secrets Handling**: Environment variables, never in code or logs

## Common Patterns

### Server Startup with Verification
```bash
# Start server
uv run python -m app.main_server &
SERVER_PID=$!

# Wait and verify
for i in {1..30}; do
    if curl -s http://localhost:PORT/endpoint; then
        echo "Ready"
        exit 0
    fi
    sleep 1
done
```

### Process Termination with Verification
```bash
# Graceful shutdown
pkill -TERM -f "pattern"
sleep 2

# Verify and force if needed
if pgrep -f "pattern"; then
    pkill -KILL -f "pattern"
fi

# Double check
if pgrep -f "pattern"; then
    echo "Failed to stop"
    exit 1
fi
```

### Docker Container Management
```bash
# Check if docker available
if ! command -v docker &> /dev/null; then
    warn "Docker not available in this environment"
    return 0
fi

# Stop with verification
docker stop container_name
for i in {1..10}; do
    if ! docker ps -q -f name=container_name | grep -q .; then
        break
    fi
    sleep 1
done
```

### Registry Pattern Implementation
```python
class BaseRegistry(ABC):
    def __init__(self, registry_dir, logger):
        self.registry_dir = Path(registry_dir)
        self.logger = logger
        self._setup_jinja_env()
        self._load_items()
    
    @abstractmethod
    def _load_items(self):
        """Implemented by subclasses"""
        pass
```

## Improvement Workflow

### Phase 1: Analysis
- Read existing documentation (README, PROJECT_SPEC, related docs)
- Understand current architecture and patterns
- Identify pain points and inconsistencies
- Review test coverage and structure

### Phase 2: Planning
- Create todo list with specific, actionable items
- Prioritize by impact and dependencies
- Mark ONE item in-progress before starting
- Document trade-offs and design decisions

### Phase 3: Implementation
- Make targeted changes, avoid scope creep
- Update tests immediately after code changes
- Run relevant test subsets frequently
- Mark todos completed IMMEDIATELY after finishing

### Phase 4: Verification
- Run full test suite with servers (`--with-servers`)
- Check launch configurations work
- Verify documentation accuracy
- Test server startup/shutdown scripts

### Phase 5: Documentation
- Update affected markdown files
- Keep cross-references synchronized
- Add inline comments for complex changes
- Update configuration examples

## Red Flags to Watch For

- ❌ **Duplicated Logic**: Extract to base class or shared utility
- ❌ **Hardcoded Values**: Use config, environment variables, or constants
- ❌ **Silent Failures**: Always log errors, provide recovery strategies
- ❌ **Information Leakage**: Generic errors for security boundaries
- ❌ **Missing Type Hints**: All function signatures need types
- ❌ **Blocking I/O**: Use async for all external operations
- ❌ **Test Dependencies**: Each test should be independent
- ❌ **Partial Updates**: Complete the full change cycle (code → tests → docs)

## Tools & Scripts

### Essential Scripts
- `scripts/run_tests.sh --with-servers`: Run full test suite with server startup
- `scripts/start-test-env.sh`: Start the ephemeral compose test stack used by integration tests
- `app/management/token_manager.py`: JWT token lifecycle management (use gofr-common auth tooling)

### Development Commands
```bash
# Run specific test category
uv run pytest test/{category}/ -v

# Check test coverage
uv run pytest --cov=app --cov-report=term-missing

# Format code
uv run black app/ test/

# Type checking
uv run mypy app/

# Start single server with debugging
python -m app.main_mcp --no-auth --port 8010
```

## Key Metrics

- **Test Count**: 300+ tests (all passing)
- **Test Categories**: Unit, Integration, Security, Workflow, Concurrency
- **Server Ports**: MCP 8010, Web 8012, MCPO 8011, n8n 5678, OpenWebUI 9090
- **Documentation Files**: 10 consolidated markdown files
- **Launch Configurations**: 17 organized VS Code configs
- **Python Version**: 3.11+ (async/await, Pydantic v2)

## Success Criteria

✅ **Code Quality**
- Type-safe throughout
- Async-first architecture
- DRY principle applied
- Comprehensive error handling

✅ **Testing**
- All tests passing
- Security tests included
- End-to-end workflows covered
- Integration tests with servers

✅ **Documentation**
- Cross-references accurate
- Examples up-to-date
- No duplicated content
- Clear navigation structure

✅ **Operations**
- Server scripts work reliably
- Health checks verify startup
- Cleanup scripts 100% effective
- Launch configs match descriptions

✅ **Security**
- Multi-tenant isolation enforced
- No information leakage
- JWT token lifecycle managed
- Directory isolation implemented
