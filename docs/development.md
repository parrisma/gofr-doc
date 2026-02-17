# DOCO Development Guide

> **Related Documentation:**
> - [← Back to README](../readme.md#-documentation) | [Project Specification](project_spec.md) | [Configuration](../app/config_docs.py)
> - **Features**: [Features Guide](features.md)
> - **Deployment**: [Docker](docker.md) | [Authentication](authentication.md)
> - **Integration**: [Integration Guide](integrations.md)

## Table of Contents
1. [Getting Started](#getting-started)
2. [Project Architecture](#project-architecture)
3. [Development Workflow](#development-workflow)
4. [Code Quality Standards](#code-quality-standards)
5. [Testing Strategy](#testing-strategy)
6. [Common Tasks](#common-tasks)
7. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites
- Python 3.11+
- uv (Python package installer)
- Git

### Initial Setup
```bash
# Clone the repository
git clone https://github.com/parrisma/doco.git
cd doco

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Run tests to verify setup
bash scripts/run_tests.sh --with-servers
```

### Configuration
See `app/config_docs.py` for comprehensive configuration documentation:
```bash
python app/config_docs.py  # Shows all environment variables and usage
```

## Project Architecture

### Directory Structure
```
doco/
├── app/                    # Application source code
│   ├── auth/              # Authentication and JWT handling
│   ├── exceptions/        # Custom exception classes
│   ├── fragments/         # Fragment registry
│   ├── logger/            # Structured logging
│   ├── mcpo/              # MCPO wrapper (OpenAPI gateway)
│   ├── rendering/         # Document rendering engine
│   ├── sessions/          # Session management
│   ├── storage/           # File storage abstraction
│   ├── styles/            # Style registry
│   ├── templates/         # Template registry
│   ├── validation/        # Pydantic models and validators
│   ├── config.py          # Configuration management
│   ├── config_docs.py     # Configuration documentation
│   ├── mcp_server.py      # MCP server implementation
│   ├── web_server.py      # FastAPI web server
│   └── main_*.py          # Entry points
│
├── data/                   # Persistent data (gitignored)
│   ├── auth/              # JWT tokens
│   ├── sessions/          # Document sessions
│   └── storage/           # Uploaded/rendered documents
│
├── docs/                   # Documentation
│   ├── project_spec.md    # Comprehensive specification
│   ├── development.md     # This file
│   └── *.md               # Feature-specific docs
│
├── templates/              # Document templates
│   └── {template_name}/   # Template bundles
│       ├── template.yaml  # Template metadata
│       ├── document.html.jinja2
│       └── fragments/     # Fragment templates
│
├── styles/                 # Visual styles
│   └── {style_name}/      # Style bundles
│       ├── style.yaml     # Style metadata
│       └── style.css      # Stylesheet
│
├── test/                   # Test suite
│   ├── test_code_quality.py  # Linting & type checking
│   ├── conftest.py        # Pytest fixtures
│   └── */                 # Feature-specific tests
│
└── scripts/                # Utility scripts
    ├── run_tests.sh       # Test execution
    └── *.py               # Helper scripts
```

### Key Components

#### 1. MCP Server (`app/mcp_server.py`)
- Implements Model Context Protocol for LLM integration
- 18 tool handlers for document generation workflow
- Group-based authentication and multi-tenancy
- Built on Starlette/FastAPI

#### 2. Session Manager (`app/sessions/`)
- Manages document creation lifecycle
- Persistence via storage layer
- Group isolation for multi-tenancy
- Fragment management

#### 3. Template System (`app/templates/`)
- Jinja2-based templating
- Pydantic schema validation
- Fragment composition
- YAML-based configuration

#### 4. Rendering Engine (`app/rendering/`)
- HTML → PDF (WeasyPrint)
- HTML → Markdown (html2text)
- Style application
- Image handling

#### 5. Validation Layer (`app/validation/`)
- Pydantic v2 models
- Input/output schemas
- Error messages with recovery strategies

## Development Workflow

### Branch Strategy
- `main`: Stable, production-ready code
- Feature branches: `feature/your-feature-name`
- Bug fixes: `fix/issue-description`

### Making Changes

1. **Create a Branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Write Code**
   - Follow PEP 8 style guide
   - Add type hints
   - Write docstrings
   - Keep functions focused and small

3. **Run Tests Locally**
   ```bash
   # Quick test run (no servers)
   pytest test/
   
   # Full test suite with MCP/Web servers
   bash scripts/run_tests.sh --with-servers
   
   # Code quality checks
   pytest test/test_code_quality.py
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   # Use conventional commits: feat:, fix:, docs:, test:, refactor:
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/my-feature
   # Create pull request on GitHub
   ```

## Code Quality Standards

### Zero Tolerance Policy
The project enforces **zero tolerance** for:
- **Linting errors** (via ruff)
- **Type errors** (via pyright/Pylance)

These are enforced by `test/test_code_quality.py`:
```bash
pytest test/test_code_quality.py
```

### Linting with Ruff
```bash
# Check for issues
ruff check app test scripts

# Auto-fix issues
ruff check --fix app test scripts

# Format code
ruff format app test scripts
```

### Type Checking with Pyright
```bash
# Check all code
pyright app test scripts

# Check specific file
pyright app/mcp_server.py
```

### Suppressing False Positives
When absolutely necessary:
```python
# Linting
result = some_function()  # noqa: E501 - Long line needed for readability

# Type checking
data = {"key": 123}  # type: ignore[arg-type] - test uses simplified format
```

**Always include a comment explaining WHY the suppression is needed!**

## Testing Strategy

### Test Structure
```
test/
├── test_code_quality.py      # Linting & type checking
├── conftest.py               # Shared fixtures
├── auth/                     # Auth tests
├── mcp/                      # MCP tool tests
├── render/                   # Rendering tests
├── storage/                  # Storage tests
├── validation/               # Validation tests
├── web/                      # Web API tests
└── workflow/                 # End-to-end tests
```

### Running Tests

```bash
# All tests (quick, no servers)
pytest

# All tests with servers (comprehensive)
bash scripts/run_tests.sh --with-servers

# Specific test file
pytest test/mcp/test_session_lifecycle.py

# Specific test
pytest test/mcp/test_session_lifecycle.py::test_create_session

# With coverage
pytest --cov=app --cov-report=html

# Code quality only
pytest test/test_code_quality.py
```

### Test Fixtures
Common fixtures in `conftest.py`:
- `tmp_data_dir`: Temporary data directory
- `test_logger`: Logger instance
- `template_registry`: Pre-loaded templates
- `session_manager`: Configured session manager

### Writing Tests
```python
import pytest
from app.sessions import SessionManager


class TestMyFeature:
    """Test suite for my feature."""
    
    @pytest.mark.asyncio
    async def test_basic_behavior(self, session_manager):
        """Test basic behavior of the feature."""
        # Arrange
        session_id = "test-session"
        
        # Act
        result = await session_manager.some_method(session_id)
        
        # Assert
        assert result is not None
        assert result.status == "success"
```

## Common Tasks

### Adding a New MCP Tool

1. **Add Tool Definition** (`app/mcp_server.py` - `handle_list_tools()`)
   ```python
   Tool(
       name="my_new_tool",
       description="Clear description of what it does...",
       inputSchema={...},
   )
   ```

2. **Add Handler Function**
   ```python
   async def _tool_my_new_tool(arguments: Dict[str, Any]) -> ToolResponse:
       payload = MyInputModel.model_validate(arguments)
       # ... implementation
       return _success(_model_dump(output))
   ```

3. **Register in HANDLERS dict**
   ```python
   HANDLERS = {
       ...
       "my_new_tool": _tool_my_new_tool,
   }
   ```

4. **Add Tests**
   ```python
   # test/mcp/test_my_new_tool.py
   async def test_my_new_tool():
       response = await call_mcp_tool("my_new_tool", {...})
       assert response["status"] == "success"
   ```

### Adding a Template Fragment

1. **Create Fragment Template**
   ```
   templates/my_template/fragments/my_fragment.html.jinja2
   ```

2. **Add to template.yaml**
   ```yaml
   fragments:
     - fragment_id: my_fragment
       name: "My Fragment"
       description: "..."
       parameters:
         - name: param1
           type: string
           required: true
   ```

3. **Add Validation Model** (if complex parameters)
   ```python
   # app/validation/document_models.py
   class MyFragmentParams(BaseModel):
       param1: str
       param2: Optional[int] = None
   ```

4. **Test the Fragment**
   ```python
   async def test_my_fragment():
       output = await manager.add_fragment(
           session_id="test",
           fragment_id="my_fragment",
           parameters={"param1": "value"}
       )
       assert output.fragment_instance_guid is not None
   ```

### Adding Environment Configuration

1. **Document in `app/config_docs.py`**
   ```python
   # Add to comments section
   # MY_NEW_VAR: Description of what it does (default: value)
   ```

2. **Add Default**
   ```python
   DEFAULT_MY_VAR = "default_value"
   ```

3. **Use in Code**
   ```python
   import os
   value = os.getenv("DOCO_MY_VAR", DEFAULT_MY_VAR)
   ```

4. **Update Configuration Summary**
   ```python
   def get_config_summary() -> dict:
       return {
           ...
           "my_var": os.getenv("DOCO_MY_VAR", DEFAULT_MY_VAR),
       }
   ```

## Troubleshooting

### Tests Failing

**Linting Errors**
```bash
# See what's wrong
ruff check app test scripts

# Auto-fix
ruff check --fix app test scripts
```

**Type Errors**
```bash
# Check types
pyright app test scripts

# Common fixes:
# - Add type hints
# - Use Optional[] for nullable values
# - Add # type: ignore[specific-error] with explanation
```

**Test Servers Not Starting**
```bash
# Check if ports are available
lsof -i :8012  # Web server
lsof -i :8010  # MCP server

# Kill existing processes
kill -9 <PID>

# Check logs
cat /tmp/mcp_server_test.log
cat /tmp/web_server_test.log
```

### Development Server Issues

**Port Already in Use**
```bash
# Find process using port
lsof -i :8011

# Kill it
kill -9 <PID>
```

**Data Directory Issues**
```bash
# Check permissions
ls -la data/

# Reset data directory
rm -rf data/*
mkdir -p data/auth data/sessions data/storage
```

**Authentication Problems**
```bash
# Generate new JWT secret
export DOCO_JWT_SECRET=$(openssl rand -hex 32)

# Or disable auth for development
export DOCO_MCPO_MODE=public
```

### Common Error Messages

**"SESSION_NOT_FOUND"**
- Session doesn't exist
- Session belongs to different group
- Solution: Call `list_active_sessions` to see available sessions

**"TEMPLATE_NOT_FOUND"**
- Template ID typo
- Template not loaded
- Solution: Call `list_templates` for valid IDs

**"INVALID_ARGUMENTS"**
- Missing required parameters
- Wrong parameter types
- Solution: Check tool's `inputSchema`, use `get_template_details`

## Additional Resources

- **Project Specification**: `docs/project_spec.md`
- **Configuration Reference**: Run `python app/config_docs.py`
- **API Documentation**: Start servers and visit:
  - MCP: `http://localhost:8010/mcp`
  - Web: `http://localhost:8012/docs`
- **n8n Integration**: `docs/integrations.md`

## Getting Help

1. Check existing documentation in `docs/`
2. Review test files for examples
3. Check issue tracker on GitHub
4. Ask in project discussions

---

**Happy Coding! 🚀**
