# n8n Integration Guide

> **Related Documentation:**
> - [← Back to README](../readme.md#integration) | [Document Generation](document_generation.md) | [Authentication](authentication.md)
> - **Deployment**: [Docker](docker.md) | [Development Guide](development.md)
> - **Features**: [Tables](features.md#tables) | [Proxy Mode](features.md#proxy-mode)

## Overview

Gofr-Doc integrates with n8n for automated document generation workflows. Two integration methods are available:

- **[HTTP REST API](#http-rest-api-recommended)** - Standard HTTP requests (recommended for n8n)
- **[MCP Protocol](#mcp-protocol)** - Model Context Protocol for AI assistants

## Quick Start

### Prerequisites

- ✅ Gofr-Doc server running (MCP on `localhost:8010`, Web on `localhost:8012`)
- ✅ n8n instance running
- ✅ Bearer token for authentication (if auth enabled)

### Test Bearer Token

For development/testing:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss
```

- **Group**: n8n
- **Expires**: November 11, 2026

---

## HTTP REST API (Recommended)

The Web API (port 8012) provides standard REST endpoints that work reliably with n8n.

### Complete Workflow Example

#### Step 1: Create Document Session with Alias

```json
POST http://localhost:8010/sessions

Headers:
  Content-Type: application/json
  Authorization: Bearer <your-token>

Body:
{
  "template_id": "basic_report",
  "alias": "q4-report"
}

Response:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "alias": "q4-report",
  "template_id": "basic_report",
  "status": "active"
}
```

💡 **Tip**: Use `alias` (e.g., "q4-report") instead of UUIDs in subsequent requests!
```

#### Step 2: Set Global Parameters

Use the alias from Step 1:

```json
POST http://localhost:8012/sessions/q4-report/parameters

Headers:
  Content-Type: application/json
  Authorization: Bearer <your-token>

Body:
{
  "title": "Q4 2024 Report",
  "author": "John Smith",
  "date": "2024-12-31"
}

Response:
{
  "status": "success",
  "message": "Global parameters updated"
}
```

#### Step 3: Add Fragments

**Text Fragment:**
```json
POST http://localhost:8012/sessions/q4-report/fragments

Headers:
  Content-Type: application/json
  Authorization: Bearer <your-token>

Body:
{
  "fragment_id": "paragraph",
  "parameters": {
    "content": "This report summarizes Q4 performance metrics."
  }
}
```

**Table Fragment:**
```json
POST http://localhost:8012/sessions/q4-report/fragments

Body:
{
  "fragment_id": "data_table",
  "parameters": {
    "rows": [
      ["Metric", "Q3", "Q4"],
      ["Revenue", "1250000", "1380000"],
      ["Profit", "400000", "460000"]
    ],
    "has_header": true,
    "title": "Financial Summary",
    "number_format": {
      "1": "currency:USD",
      "2": "currency:USD"
    },
    "zebra_stripe": true
  }
}
```

**Image Fragment:**
```json
POST http://localhost:8012/sessions/q4-report/fragments/images

Body:
{
  "image_url": "https://example.com/chart.png",
  "title": "Performance Chart",
  "width": 600,
  "alignment": "center"
}
```

#### Step 4: Render Document

```json
POST http://localhost:8012/sessions/q4-report/render

Headers:
  Content-Type: application/json
  Authorization: Bearer <your-token>

Body:
{
  "format": "pdf",
  "style_id": "default"
}

Response:
{
  "status": "success",
  "format": "pdf",
  "content": "<base64-encoded-pdf>"
}
```

**With Proxy Mode** (for large documents):
```json
Body:
{
  "format": "pdf",
  "style_id": "default",
  "proxy": true
}

Response:
{
  "status": "success",
  "format": "pdf",
  "content": "",
  "proxy_guid": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Document stored in proxy mode"
}
```

### n8n HTTP Request Node Setup

#### Basic Configuration

1. **Add HTTP Request Node** to workflow
2. **Configure**:
   - Method: POST
   - URL: `http://localhost:8012/sessions`
   - Authentication: Generic Credential Type → Header Auth
     - Name: `Authorization`
     - Value: `Bearer <your-token>`
   - Body: JSON

3. **Example Body**:
```json
{
  "template_id": "basic_report"
}
```

#### Dynamic Data Example

Use n8n expressions to pass data from previous nodes:

```json
{
  "fragment_id": "data_table",
  "parameters": {
    "rows": {{ $json.tableData }},
    "has_header": true,
    "title": "{{ $json.chartTitle }}",
    "zebra_stripe": true
  }
}
```

### API Endpoints Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sessions` | POST | Create document session |
| `/sessions/{id}/parameters` | POST | Set global parameters |
| `/sessions/{id}/fragments` | POST | Add text/table fragment |
| `/sessions/{id}/fragments/images` | POST | Add image fragment |
| `/sessions/{id}/fragments` | GET | List fragments |
| `/sessions/{id}/fragments/{guid}` | DELETE | Remove fragment |
| `/sessions/{id}/render` | POST | Render document |
| `/sessions/{id}` | GET | Get session status |
| `/sessions/{id}` | DELETE | Abort session |
| `/sessions` | GET | List active sessions |
| `/templates` | GET | List templates |
| `/templates/{id}` | GET | Get template details |
| `/styles` | GET | List styles |

### Error Handling

#### Common HTTP Status Codes

- **200 OK** - Success
- **400 Bad Request** - Invalid parameters
- **401 Unauthorized** - Missing/invalid token
- **404 Not Found** - Session/resource not found
- **500 Internal Server Error** - Server error

#### Example Error Response

```json
{
  "status": "error",
  "error_code": "PARAMETER_MISSING",
  "message": "Required parameter 'title' is missing",
  "recovery": "Provide the 'title' parameter in global parameters"
}
```

---

## MCP Protocol

The MCP server (port 8010) uses Model Context Protocol for AI assistant integrations.

### Setup

**Server URL**: `http://localhost:8010/mcp/`

**Protocol**: HTTP Streamable (SSE)

**Authentication**: Bearer token in tool arguments

### Available Tools

#### Discovery Tools (No Auth Required)

- `ping` - Health check
- `list_templates` - List available templates
- `get_template_details` - Get template schema
- `list_styles` - List available styles

#### Session Tools (Auth Required)

- `create_document_session` - Start new session
- `set_global_parameters` - Set template parameters
- `add_fragment` - Add text/table fragment
- `add_image_fragment` - Add image
- `remove_fragment` - Delete fragment
- `get_document` - Render document
- `list_active_sessions` - List sessions
- `abort_document_session` - Cancel session

### Python MCP Client Example

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def generate_document():
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    async with streamablehttp_client('http://localhost:8010/mcp/') as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            
            # Create session
            result = await session.call_tool(
                'create_document_session',
                arguments={
                    'template_id': 'basic_report',
                    'token': token
                }
            )
            session_id = result.content[0].text  # Extract session_id
            
            # Set parameters
            await session.call_tool(
                'set_global_parameters',
                arguments={
                    'session_id': session_id,
                    'parameters': {'title': 'My Report'},
                    'token': token
                }
            )
            
            # Add fragment
            await session.call_tool(
                'add_fragment',
                arguments={
                    'session_id': session_id,
                    'fragment_id': 'paragraph',
                    'parameters': {'content': 'Report content'},
                    'token': token
                }
            )
            
            # Render document
            result = await session.call_tool(
                'get_document',
                arguments={
                    'session_id': session_id,
                    'format': 'pdf',
                    'token': token
                }
            )
            
            print("Document rendered successfully!")

asyncio.run(generate_document())
```

### MCP Tool Schemas

Tools follow JSON-RPC 2.0 format. Example:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_document_session",
    "arguments": {
      "template_id": "basic_report",
      "token": "eyJhbGc..."
    }
  }
}
```

---

## n8n MCP Client Node

n8n includes an MCP Client node for direct protocol integration.

### Configuration

1. **Add MCP Client Node** to workflow
2. **Configure Server**:
   - URL: `http://localhost:8010/mcp/`
   - Protocol: HTTP Streamable

3. **Call Tools**:
   - Select tool from dropdown
   - Provide arguments (including `token`)

### Known Issues & Limitations

#### ⚠️ Accept Header Requirement

The MCP server requires:
```
Accept: application/json, text/event-stream
```

n8n's MCP Client may not send this header by default, causing errors:
```json
{
  "code": -32600,
  "message": "Not Acceptable: Client must accept both application/json and text/event-stream"
}
```

**Solution**: Use HTTP Request node instead (recommended).

#### Other Limitations

- **Authentication**: Token must be in tool arguments, not headers
- **Binary Data**: Image responses may need special handling
- **Version**: Requires recent n8n with MCP support

---

## Troubleshooting

### Connection Issues

#### Test 1: Server is Running

```bash
curl http://localhost:8012/health
curl http://localhost:8010/health
```

Expected: Should connect (even if 404 response)

#### Test 2: Web API Responds

```bash
curl -X GET http://localhost:8012/templates \
  -H "Authorization: Bearer <your-token>"
```

Expected: JSON list of templates

#### Test 3: MCP Endpoint Responds

```bash
curl -X POST http://localhost:8010/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

Expected: SSE stream with tools list

### Authentication Errors

#### AUTH_REQUIRED

```json
{
  "status": "error",
  "error_code": "AUTH_REQUIRED",
  "message": "Authentication required"
}
```

**Cause**: No token provided when auth is enabled.

**Solution**: 
- Add `Authorization: Bearer <token>` header (HTTP API)
- Add `token` argument (MCP tools)
- Or run server with `--no-auth` flag (development only)

#### AUTH_FAILED - Token Expired

```json
{
  "status": "error",
  "error_code": "AUTH_FAILED",
  "message": "Token has expired"
}
```

**Solution**: Generate new token:
```bash
./scripts/token_manager.sh create --group n8n --expires 30
```

#### AUTH_FAILED - Invalid Token

**Cause**: Token signature doesn't match or malformed.

**Solution**: Verify JWT secret matches:
```bash
echo $GOFR_JWT_SECRET
```

### 2. Network Issues

If n8n is in Docker and can't reach gofr-doc:

- Use `host.docker.internal` (Mac/Windows)
- Use `172.17.0.1` (Linux)
- Or put both in same network:

```bash
# Run gofr-doc on host
./scripts/run_dev.sh

# Run n8n in docker with host network
docker run --network host n8n/n8n
```

Or with docker-compose:

```yaml
services:
  gofr-doc-web:
    container_name: gofr-doc-web
    networks:
      - ai-net
  
  n8n:
    networks:
      - ai-net
```

Then use: `http://gofr-doc-web:8012` from n8n.

### 3. Debugging

Check connectivity:
```bash
# From n8n container
docker exec -it n8n sh

# Try to reach gofr-doc
ping gofr-doc-web
curl http://gofr-doc-web:8012/health
```

Check logs:
```bash
# Gofr-Doc logs
docker logs gofr-doc-web -f
docker logs gofr-doc-mcp -f
```
./scripts/token_manager.sh verify --token <token>
```

### Docker Networking

If n8n is in Docker and can't reach gofr-doc:

#### Option 1: Use Host Network
```bash
# Run gofr-doc on host
python -m app.main_web --host 0.0.0.0

# From n8n container, use host.docker.internal
curl http://host.docker.internal:8012/templates
```

#### Option 2: Docker Compose Network
```yaml
services:
  gofr-doc-web:
    container_name: gofr-doc-web
    networks:
      - n8n_network
  
  n8n:
    networks:
      - n8n_network

networks:
  n8n_network:
```

Then use: `http://gofr-doc-web:8012` from n8n.

### Diagnostic Commands

#### Check Connectivity
```bash
# From n8n container
ping gofr-doc-web
curl http://gofr-doc-web:8012/health
```

#### List Active Sessions
```bash
curl http://localhost:8012/sessions \
  -H "Authorization: Bearer <token>"
```

#### Verify Token
```bash
./scripts/token_manager.sh verify --token <token>
```

#### Check Server Logs
```bash
# Docker
docker logs gofr-doc-web -f
docker logs gofr-doc-mcp -f

# Direct
# Check terminal output where servers are running
```

---

## Best Practices

### For n8n Workflows

1. **Use HTTP Request Node** - More reliable than MCP Client
2. **Port 8012** (Web API) - Better n8n compatibility
3. **Store Tokens Securely** - Use n8n credentials manager
4. **Handle Errors** - Check response status, implement retries
5. **Use Proxy Mode** - For large PDFs to reduce payload size

### For Production

1. **HTTPS Only** - Use reverse proxy (nginx, Caddy)
2. **Token Rotation** - Rotate tokens regularly
3. **Rate Limiting** - Implement at reverse proxy level
4. **Monitoring** - Log authentication failures
5. **Backups** - Backup session data and tokens

### Security

- ✅ Use HTTPS in production
- ✅ Store JWT secret securely
- ✅ Rotate tokens periodically
- ✅ Use short expiration times
- ✅ Monitor for auth failures
- ❌ Never use `--no-auth` in production
- ❌ Never commit tokens to git

---

## Example Workflows

### Automated Report Generation

**Trigger**: Schedule (daily at 9 AM)

**Steps**:
1. Fetch data from database
2. Transform data to table format
3. Create gofr-doc session
4. Add title parameters
5. Add table fragments
6. Render PDF
7. Email PDF to stakeholders

### Dynamic Chart Generation

**Trigger**: Webhook from monitoring system

**Steps**:
1. Receive metrics data
2. Format as chart parameters
3. Create gofr-doc session
4. Add chart image
5. Render HTML
6. Post to Slack/Teams

### Multi-Format Publishing

**Trigger**: Manual button click

**Steps**:
1. Create single session
2. Add all fragments once
3. Render as PDF
4. Render as HTML
5. Render as Markdown
6. Upload to S3/storage
7. Send notifications

---

## API Response Examples

### Successful Session Creation

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "template_id": "basic_report",
  "group": "n8n",
  "status": "active",
  "created_at": "2024-11-23T10:30:00Z"
}
```

### Successful Render

```json
{
  "status": "success",
  "format": "pdf",
  "content": "JVBERi0xLjQKJeLjz9MKMyAwIG9iago8P...",
  "size_bytes": 45231
}
```

### Successful Proxy Render

```json
{
  "status": "success",
  "format": "pdf",
  "content": "",
  "proxy_guid": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Document stored in proxy mode"
}
```

### Error Response

```json
{
  "status": "error",
  "error_code": "SESSION_NOT_FOUND",
  "message": "Session not found or expired",
  "recovery": "Create a new session with create_document_session"
}
```

---

## Additional Resources

- **[Document Generation Guide](document_generation.md)** - Complete workflow details
- **[Features Guide](features.md)** - Tables, images, proxy mode
- **[Authentication Guide](authentication.md)** - Security setup
- **[Docker Guide](docker.md)** - Container deployment
- **[Development Guide](development.md)** - Testing and development

---

## Summary

**Recommended for n8n**: Use HTTP REST API (port 8012) with HTTP Request nodes.

**Key Points**:
- ✅ HTTP API is more reliable in n8n
- ✅ MCP is better for AI assistants (Claude, etc.)
- ✅ Both methods support full functionality
- ✅ Use proxy mode for large documents
- ✅ Store tokens securely in n8n credentials
