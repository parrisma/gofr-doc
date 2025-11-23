# Authentication & Security Guide

> **Related Documentation:**
> - [← Back to README](../README.md#core-documentation) | [Project Spec](PROJECT_SPEC.md) | [Development Guide](DEVELOPMENT.md)
> - **Deployment**: [Docker](DOCKER.md) | [Configuration](../app/config_docs.py)
> - **Features**: [Features Guide](FEATURES.md) | [Data Persistence](DATA_PERSISTENCE.md)

## Quick Start

### Development Mode (No Authentication)
```bash
# Run without authentication - all operations use "public" group
python -m app.main_mcp
python -m app.main_web
```

### Production Mode (JWT Authentication)
```bash
# Set JWT secret
export DOCO_JWT_SECRET="your-secure-secret-key"
export DOCO_TOKEN_STORE="/path/to/tokens.json"

# Run with authentication enabled
python -m app.main_mcp --jwt-secret "$DOCO_JWT_SECRET" --token-store "$DOCO_TOKEN_STORE"
python -m app.main_web --jwt-secret "$DOCO_JWT_SECRET" --token-store "$DOCO_TOKEN_STORE"
```

## Authentication Methods

### 1. HTTP Authorization Header (Recommended)
Standard HTTP header approach - most secure and compatible.

```bash
# Using curl
curl -X POST http://localhost:8011/mcp/tools/call \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{"name": "create_document_session", "arguments": {...}}'
```

**Why use headers:**
- ✅ Standard HTTP/REST convention
- ✅ Secure (not logged in arguments)
- ✅ Works with proxies and gateways
- ✅ Framework-native integration

### 2. Token in Arguments (Legacy)
Backward compatible - token passed in tool arguments.

```json
{
  "name": "create_document_session",
  "arguments": {
    "template_id": "basic_report",
    "token": "eyJhbGc..."
  }
}
```

## Token Management

### Creating Tokens
```bash
# Create token for a group (expires in 30 days)
python scripts/token_manager.py create --group engineering --expires 30

# Output:
# Token created successfully!
# Bearer Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# Group: engineering
# Expires: 2025-12-23 10:30:45
```

### Listing Tokens
```bash
# View all active tokens
python scripts/token_manager.py list

# Output shows: Group, Created, Expires, Status
```

### Revoking Tokens
```bash
# Revoke a specific token
python scripts/token_manager.py revoke <token>

# Revoke all tokens for a group
python scripts/token_manager.py revoke --group engineering
```

### Verifying Tokens
```bash
# Check token validity and decode claims
python scripts/token_manager.py verify <token>

# Shows: Group, Issued At, Expires, Valid (yes/no)
```

## Security Architecture

### Group-Based Multi-Tenancy

Every authenticated request is bound to a **group** (extracted from JWT token):

```python
# JWT Token Payload
{
  "group": "engineering",    # Session isolation boundary
  "iat": 1732377600,         # Issued at timestamp
  "exp": 1734969600          # Expiration timestamp
}
```

**Security Guarantees:**
- ✅ Sessions isolated by group
- ✅ Cross-group access returns generic "SESSION_NOT_FOUND" (prevents information leakage)
- ✅ Templates, styles, fragments organized by group
- ✅ Discovery tools (list_templates, list_styles) do NOT require authentication

### Session Isolation

```
┌─────────────────────┬─────────────────────┐
│  Group: engineering │  Group: research    │
├─────────────────────┼─────────────────────┤
│  sessions:          │  sessions:          │
│  - abc-123          │  - xyz-789          │
│  - def-456          │  - uvw-012          │
├─────────────────────┼─────────────────────┤
│  templates:         │  templates:         │
│  - tech_report      │  - research_paper   │
│  - design_doc       │  - findings_summary │
└─────────────────────┴─────────────────────┘

❌ engineering token CANNOT access research sessions
❌ research token CANNOT access engineering templates
```

### Authentication Flow

```
┌────────┐         ┌──────────────┐         ┌────────────┐
│ Client │────────>│ MCP/Web      │────────>│ Session    │
│        │  Bearer │ Server       │  Group  │ Manager    │
│        │  Token  │              │  Claim  │            │
└────────┘         └──────────────┘         └────────────┘
                         │
                         ├─> Extract JWT
                         ├─> Verify signature
                         ├─> Check expiration
                         └─> Extract "group" claim
                              │
                              └─> Inject into all operations
```

## Implementation Details

### MCP Server (`app/mcp_server.py`)

**Middleware:**
```python
class AuthHeaderMiddleware(BaseHTTPMiddleware):
    """Extract Authorization header and store in context var."""
    async def dispatch(self, request, call_next):
        auth_header = request.headers.get("Authorization", "")
        token = _auth_header_context.set(auth_header)
        try:
            response = await call_next(request)
        finally:
            _auth_header_context.reset(token)
        return response
```

**Token Verification:**
```python
def _verify_auth(arguments: Dict[str, Any], require_token: bool) -> tuple[Optional[str], Optional[ToolResponse]]:
    """Extract and verify JWT token, return (group, error)"""
    # Try header first, then arguments (backward compat)
    token = _extract_token_from_context_or_args(arguments)
    
    if not token and require_token:
        return None, _error("AUTH_REQUIRED", ...)
    
    token_info = auth_service.verify_token(token)
    return token_info.group, None  # Return group from JWT
```

### Web Server (`app/web_server.py`)

FastAPI dependency injection:
```python
async def require_auth(authorization: str = Header(None)) -> str:
    """Extract and verify JWT from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    
    token = authorization[7:]  # Strip "Bearer "
    token_info = auth_service.verify_token(token)
    return token_info.group  # Return group for route handlers
```

### Token Store (`app/auth/token_store.py`)

Persistent JSON storage with atomic writes:
```python
{
  "tokens": [
    {
      "token": "eyJhbGc...",
      "group": "engineering",
      "issued_at": "2025-11-23T10:00:00Z",
      "expires_at": "2025-12-23T10:00:00Z",
      "revoked": false
    }
  ]
}
```

## Configuration

### Environment Variables

```bash
# JWT Secret (required for auth mode)
export DOCO_JWT_SECRET="your-secret-key"

# Token Store Path
export DOCO_TOKEN_STORE="/path/to/tokens.json"
# Default: {DATA_DIR}/auth/tokens.json

# Data Directory (for all persistent data)
export DOCO_DATA_DIR="/var/doco/data"
# Default: ./data
```

See [Configuration Reference](../app/config_docs.py) for all options:
```bash
python app/config_docs.py
```

## Testing with Authentication

### Test Server Setup

```bash
# Run test servers with authentication (for integration tests)
bash scripts/run_tests.sh --with-servers

# Servers start with:
# - JWT_SECRET: test-secret-key
# - Token store: /tmp/doco-test-tokens.json
# - Pre-created tokens for "public" and "private" groups
```

### Manual Testing

```bash
# 1. Generate test token
export TEST_TOKEN=$(python scripts/token_manager.py create --group test --expires 1 | grep "Bearer Token:" | cut -d' ' -f3)

# 2. Test MCP endpoint
curl -X POST http://localhost:8011/mcp/tools/call \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "create_document_session",
    "arguments": {"template_id": "basic_report"}
  }'

# 3. Test Web API
curl http://localhost:8010/templates \
  -H "Authorization: Bearer $TEST_TOKEN"
```

## Troubleshooting

### "AUTH_REQUIRED" Error
**Cause**: No token provided when authentication is enabled.

**Solution**:
```bash
# Check if auth is enabled
env | grep DOCO_JWT_SECRET

# If set, provide token via header
curl -H "Authorization: Bearer your-token-here" ...
```

### "AUTH_FAILED" - Token Expired
**Cause**: JWT token has passed its expiration time.

**Solution**:
```bash
# Create new token
python scripts/token_manager.py create --group yourgroup --expires 30
```

### "AUTH_FAILED" - Invalid Token
**Cause**: Token signature doesn't match or token is malformed.

**Solution**:
```bash
# Verify token
python scripts/token_manager.py verify <token>

# Check JWT secret matches between token creation and server
echo $DOCO_JWT_SECRET
```

### "SESSION_NOT_FOUND" (with valid token)
**Cause**: Trying to access session from different group.

**Solution**:
```bash
# List your group's sessions
# (token automatically scopes to your group)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8010/sessions

# Sessions from other groups are invisible for security
```

## Security Best Practices

### Production Deployment

1. **Strong Secret**: Use cryptographically random JWT secret
   ```bash
   export DOCO_JWT_SECRET=$(openssl rand -hex 32)
   ```

2. **Secure Storage**: Protect token store file with file permissions
   ```bash
   chmod 600 /var/doco/data/auth/tokens.json
   chown doco:doco /var/doco/data/auth/tokens.json
   ```

3. **HTTPS Only**: Use HTTPS in production (not HTTP)
   - Configure reverse proxy (nginx, Caddy)
   - Use Let's Encrypt for certificates

4. **Token Rotation**: Regularly rotate tokens
   ```bash
   # Revoke old tokens
   python scripts/token_manager.py revoke --group engineering
   
   # Create new token
   python scripts/token_manager.py create --group engineering --expires 30
   ```

5. **Monitoring**: Log authentication failures
   ```bash
   # Check server logs for auth errors
   tail -f /var/log/doco/mcp_server.log | grep AUTH_FAILED
   ```

### Docker Deployment

See [Docker Guide](DOCKER.md) for complete container setup with authentication.

```yaml
# docker-compose.yml
services:
  doco-mcp:
    environment:
      - DOCO_JWT_SECRET=${DOCO_JWT_SECRET}
      - DOCO_TOKEN_STORE=/data/auth/tokens.json
    volumes:
      - doco-data:/data
    secrets:
      - jwt_secret

secrets:
  jwt_secret:
    file: ./secrets/jwt_secret.txt
```

## API Reference

### Tools Requiring Authentication

All session operations require authentication:
- `create_document_session`
- `set_global_parameters`
- `add_fragment`
- `add_image_fragment`
- `remove_fragment`
- `list_session_fragments`
- `abort_document_session`
- `get_document`
- `get_session_status`
- `list_active_sessions`
- `validate_parameters`

### Tools NOT Requiring Authentication

Discovery tools are public:
- `ping`
- `help`
- `list_templates`
- `get_template_details`
- `list_template_fragments`
- `get_fragment_details`
- `list_styles`

## See Also

- **[Features Guide](FEATURES.md#groups)** - Group-based resource organization
- **[Data Persistence](DATA_PERSISTENCE.md)** - Session storage and recovery
- **[Docker Deployment](DOCKER.md)** - Container setup with secrets
- **[Configuration](../app/config_docs.py)** - Environment variables reference
- **[Development Guide](DEVELOPMENT.md)** - Testing with authentication

---

For implementation details, see:
- `app/auth/service.py` - JWT verification logic
- `app/auth/token_store.py` - Persistent token storage
- `app/mcp_server.py` - MCP authentication flow
- `app/web_server.py` - Web API authentication
- `scripts/token_manager.py` - Token management CLI
