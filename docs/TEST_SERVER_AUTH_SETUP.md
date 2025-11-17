# Test Server Setup for Secure (Auth) Mode Testing

This document describes how to run tests with secure (auth-enabled) MCP and web servers.

## Overview

When testing the MCP and web servers in production-like conditions, they should run with authentication enabled. The test infrastructure provides:

1. **Shared JWT Secret**: All test servers and token generation use the same secret
2. **Token Generation**: Tests can generate valid JWT tokens for authenticated requests
3. **Server Management**: Fixtures for starting/stopping servers with auth enabled
4. **Auth Helpers**: Utility functions for adding auth headers to HTTP requests

## Quick Start

### 1. Set Environment Variables

Before running tests, set these environment variables:

```bash
export DOCO_JWT_SECRET="test-secret-key-for-secure-testing-do-not-use-in-production"
export DOCO_TOKEN_STORE="/tmp/doco_test_tokens.json"
```

These are automatically set by conftest.py before tests run.

### 2. Run Tests

Standard pytest commands work as usual:

```bash
# Run all tests
pytest

# Run specific test file
pytest test/web/test_document_generation.py

# Run with auth-enabled servers (see manual server launch below)
pytest
```

### 3. Using Test Fixtures

#### Get a JWT Token

```python
@pytest.mark.asyncio
async def test_with_auth(test_jwt_token):
    """Test function receives a valid JWT token"""
    # test_jwt_token is a string containing a valid JWT
    assert isinstance(test_jwt_token, str)
```

#### Use Token in Requests

```python
from test.auth_helpers import add_auth_header

@pytest.mark.asyncio
async def test_api_call(test_jwt_token):
    """Make authenticated API requests"""
    import httpx
    
    headers = add_auth_header(test_jwt_token)
    # or: headers = {"Authorization": f"Bearer {test_jwt_token}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/documents",
            headers=headers
        )
```

#### Use Auth Helper Functions

```python
from test.auth_helpers import authenticated_get

@pytest.mark.asyncio
async def test_with_helpers(test_jwt_token):
    """Use provided helper functions"""
    response = await authenticated_get(
        "http://localhost:8000/api/documents",
        test_jwt_token
    )
```

### 4. Starting Test Servers Manually (Optional)

If you want to run servers in auth mode for manual testing or integration tests:

#### Start MCP Server in Auth Mode

```bash
export DOCO_JWT_SECRET="test-secret-key-for-secure-testing-do-not-use-in-production"
export DOCO_TOKEN_STORE="/tmp/doco_test_tokens.json"

python app/main_mcp.py \
    --templates-dir data/docs/templates \
    --styles-dir data/docs/styles \
    --storage-dir data/storage \
    --port=8013
```

#### Start Web Server in Auth Mode

```bash
export DOCO_JWT_SECRET="test-secret-key-for-secure-testing-do-not-use-in-production"
export DOCO_TOKEN_STORE="/tmp/doco_test_tokens.json"

python app/main_web.py \
    --templates-dir data/docs/templates \
    --styles-dir data/docs/styles \
    --storage-dir data/storage \
    --port=8000
```

#### Generate Tokens for Manual Testing

```python
from app.auth import AuthService

# Use same secret as servers
auth_service = AuthService(
    secret_key="test-secret-key-for-secure-testing-do-not-use-in-production",
    token_store_path="/tmp/doco_test_tokens.json"
)

# Create a token
token = auth_service.create_token(group="test_group", expires_in_seconds=3600)
print(f"Token: {token}")

# Use in requests
import httpx
headers = {"Authorization": f"Bearer {token}"}
response = httpx.get("http://localhost:8000/api/documents", headers=headers)
```

## Configuration Reference

### Test Constants (in test/conftest.py)

| Constant | Value | Usage |
|----------|-------|-------|
| `TEST_JWT_SECRET` | `test-secret-key-for-secure-testing-do-not-use-in-production` | Shared JWT secret for all components |
| `TEST_TOKEN_STORE_PATH` | `/tmp/doco_test_tokens.json` | Path to persistent token store |
| `TEST_GROUP` | `test_group` | Default group for test tokens |

### Environment Variables (Auto-set by conftest.py)

| Variable | Default | Used By |
|----------|---------|---------|
| `DOCO_JWT_SECRET` | See TEST_JWT_SECRET | Servers, AuthService |
| `DOCO_TOKEN_STORE` | See TEST_TOKEN_STORE_PATH | Servers, AuthService |

## Test Fixtures

### `test_jwt_token` (Function-Scoped)

Provides a valid JWT token for the duration of a test.

- **Scope**: Function (new token per test)
- **Lifecycle**: Created at test start, revoked at test end
- **Returns**: String containing valid JWT token
- **Example**:
  ```python
  def test_something(test_jwt_token):
      headers = {"Authorization": f"Bearer {test_jwt_token}"}
      # Use in requests
  ```

### `test_auth_service` (Session-Scoped)

Provides an AuthService instance with shared JWT secret and token store.

- **Scope**: Session (same instance for all tests)
- **Returns**: AuthService instance
- **Example**:
  ```python
  def test_something(test_auth_service):
      token = test_auth_service.create_token(group="test_group")
      # Use token in requests
  ```

### `test_server_manager` (Session-Scoped)

Provides TestServerManager for starting/stopping servers in auth mode.

- **Scope**: Session
- **Returns**: TestServerManager instance (or None if import failed)
- **Methods**:
  - `start_mcp_server(templates_dir, styles_dir, storage_dir=None) -> bool`
  - `start_web_server(templates_dir, styles_dir, storage_dir=None) -> bool`
  - `stop_mcp_server()`
  - `stop_web_server()`
  - `stop_all()`
  - `get_mcp_url() -> str`
  - `get_web_url() -> str`
- **Example**:
  ```python
  def test_with_server(test_server_manager, test_data_dir, test_jwt_token):
      # Start server
      success = test_server_manager.start_mcp_server(
          templates_dir=str(test_data_dir / "docs/templates"),
          styles_dir=str(test_data_dir / "docs/styles"),
      )
      if not success:
          pytest.skip("MCP server failed to start")
      
      # Use server with auth token
      url = test_server_manager.get_mcp_url()
      headers = {"Authorization": f"Bearer {test_jwt_token}"}
      response = httpx.get(f"{url}status", headers=headers)
      assert response.status_code == 200
  ```

### `configure_test_auth_environment` (Session-Scoped, Auto-Used)

Automatically configures environment variables before all tests.

- **Scope**: Session (runs once before all tests)
- **Autouse**: Yes (runs automatically)
- **Configures**:
  - `DOCO_JWT_SECRET`
  - `DOCO_TOKEN_STORE`
- **Side Effects**: Creates token store directory

### `test_data_dir` (Function-Scoped, Auto-Used)

Automatically provides temporary data directory for each test.

- **Scope**: Function (new directory per test)
- **Autouse**: Yes (runs automatically)
- **Creates**: Temporary directory with storage and auth subdirectories
- **Cleanup**: Purges all documents after test, removes directory
- **Note**: Automatically configured for tests, available via fixture parameter

## Key Security Notes

⚠️ **Important**: These are TEST SECRETS only!

- `TEST_JWT_SECRET` should NEVER be used in production
- `TEST_TOKEN_STORE_PATH` is a temporary file for testing only
- Use different secrets and secure token stores in production
- Remove test mode flags before deploying to production

## Troubleshooting

### Server fails to start

1. Check port availability:
   ```bash
   lsof -i :8013  # MCP port
   lsof -i :8000  # Web port
   ```

2. Check environment variables are set:
   ```bash
   echo $DOCO_JWT_SECRET
   echo $DOCO_TOKEN_STORE
   ```

3. Check token store directory exists:
   ```bash
   mkdir -p /tmp
   ls -la /tmp/doco_test_tokens.json
   ```

### Token generation fails

1. Ensure TEST_JWT_SECRET matches across all components
2. Check token store is writable:
   ```bash
   touch /tmp/doco_test_tokens.json
   chmod 666 /tmp/doco_test_tokens.json
   ```

### Tests fail with 401 Unauthorized

1. Ensure test_jwt_token fixture is used
2. Verify token is passed in Authorization header:
   ```python
   headers = {"Authorization": f"Bearer {test_jwt_token}"}
   ```
3. Check token hasn't expired (test_jwt_token is valid for 1 hour)

### Tests timeout waiting for server

1. Ensure server started successfully (check for errors above)
2. Increase timeout in test_server_manager._wait_for_server (currently 10 seconds)
3. Check firewall/network rules aren't blocking localhost:8013 or :8000

## Integration with CI/CD

For continuous integration, ensure:

1. Environment variables are set before running tests:
   ```yaml
   env:
     DOCO_JWT_SECRET: test-secret-key-for-secure-testing-do-not-use-in-production
     DOCO_TOKEN_STORE: /tmp/doco_test_tokens.json
   ```

2. Temporary directory /tmp is writable (usually true on CI systems)

3. Ports 8013 and 8000 are available (usually true in isolated CI containers)

## See Also

- `test/conftest.py` - Pytest fixtures and configuration
- `test/test_server_manager.py` - TestServerManager class
- `test/auth_helpers.py` - Authentication helper functions
- `app/auth/service.py` - AuthService implementation
