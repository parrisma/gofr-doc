# N8N MCP Client Troubleshooting

## Common Error: "Error in sub-node 'MCP DOCO Client'"

### Root Cause

The doco MCP server requires specific HTTP headers that N8N's MCP Client may not be sending by default:

```
Accept: application/json, text/event-stream
```

If these headers are missing, you'll get:
```json
{
  "code": -32600,
  "message": "Not Acceptable: Client must accept both application/json and text/event-stream"
}
```

## Solutions

### Solution 1: Use HTTP Request Node Instead (Recommended)

N8N's HTTP Request node gives you full control over headers and is more reliable:

**Configuration:**
1. Add **HTTP Request** node
2. **URL**: `http://localhost:8010/render` (use Web API, not MCP)
3. **Method**: POST
4. **Authentication**: Generic Credential Type
   - Type: Header Auth
   - Name: `Authorization`
   - Value: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss`
5. **Body**:
```json
{
  "title": "My Chart",
  "x": [1, 2, 3, 4, 5],
  "y": [10, 25, 15, 30, 20],
  "type": "bar"
}
```

**Pros:**
- ✅ Simple and reliable
- ✅ Full control over requests
- ✅ Better error messages
- ✅ More N8N features (retry, timeout, etc.)

**Cons:**
- ❌ Not using MCP protocol
- ❌ No auto-discovery of tools

### Solution 2: Run Server with --no-auth Flag

If authentication is causing issues, you can run the servers without auth:

```bash
# MCP Server without authentication
python -m app.main_mcp --no-auth --host 0.0.0.0 --port 8011

# Web Server without authentication  
python -m app.main_web --no-auth --host 0.0.0.0 --port 8010
```

Then you don't need to pass tokens in requests.

**⚠️ Warning**: Only use `--no-auth` in development/trusted environments!

### Solution 3: Check N8N MCP Client Configuration

If you must use the MCP Client node:

1. **Verify URL format:**
   - Try: `http://localhost:8011/mcp/`
   - Try: `http://localhost:8011/mcp`
   - Try: `http://host.docker.internal:8011/mcp/` (if N8N in Docker)

2. **Check N8N version:**
   - MCP support was added recently
   - Ensure you have latest N8N version
   - Check N8N documentation for MCP Client requirements

3. **Test server accessibility:**
```bash
# From N8N container or machine
curl -X POST http://localhost:8011/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"n8n","version":"1.0"}}}'
```

Should return:
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{...}}
```

4. **Check N8N logs:**
   - Look for HTTP request details
   - Check what headers N8N is sending
   - Verify N8N can reach the server

## Diagnostic Commands

### Test 1: Server is Running
```bash
curl http://localhost:8011/health 2>&1
```

Expected: Should connect (even if 404)

### Test 2: MCP Endpoint Responds
```bash
curl -X POST http://localhost:8011/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' 2>&1
```

Expected: Should return list of tools

### Test 3: Token Authentication Works
```bash
python -c "
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def test():
    token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss'
    async with streamablehttp_client('http://localhost:8011/mcp/') as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool('ping', arguments={'token': token})
            print('✓ MCP Server working correctly')
            print(f'  Response: {result.content[0].text}')

asyncio.run(test())
"
```

Expected: Should print success message

## Alternative: Web API Usage

The **Web API is the recommended approach** for N8N integration:

### Example: Simple Request

```bash
curl -X POST http://localhost:8010/render \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss" \
  -d '{
    "title": "Test Chart",
    "x": [1, 2, 3, 4, 5],
    "y": [10, 20, 15, 25, 20],
    "type": "bar"
  }'
```

### N8N HTTP Request Node Setup

1. **Method**: POST
2. **URL**: `http://localhost:8010/render`
3. **Headers**:
   - `Content-Type`: `application/json`
   - `Authorization`: `Bearer <your-token>`
4. **Body**:
```json
{
  "title": "{{ $json.title }}",
  "x": {{ $json.x }},
  "y": {{ $json.y }},
  "type": "{{ $json.type }}"
}
```

5. **Response**:
   - Parse as JSON
   - Image data in `image_data` field (base64)
   - Format in `format` field

## Known Issues & Limitations

### N8N MCP Client Limitations

1. **Header Control**: N8N's MCP Client may not let you customize Accept headers
2. **Authentication**: Token must be passed in tool arguments, not headers
3. **Binary Data**: Image responses may need special handling
4. **Version Compatibility**: Requires recent N8N version with MCP support

### Workarounds

- **Use HTTP Request node** for production workflows
- **Use MCP Client** only for testing/exploration
- **Run without auth** in trusted environments
- **Use proxy mode** to get GUID instead of binary data

## Getting More Help

1. **Check N8N Logs**:
   - Look in N8N's workflow execution logs
   - Check N8N's server logs (Docker logs if containerized)

2. **Check doco Logs**:
```bash
# Check MCP server logs
docker logs doco_mcp_dev -f

# Or if running directly
# Look at terminal output where server is running
```

3. **Verify Network**:
```bash
# From N8N container
ping doco_dev
curl http://doco_dev:8011/mcp/
```

4. **Check Token**:
```bash
# List all tokens
python scripts/token_manager.py --secret "test-secret-key-for-auth-testing" \
  --token-store /tmp/doco_test_tokens.json list

# Verify specific token
python scripts/token_manager.py --secret "test-secret-key-for-auth-testing" \
  --token-store /tmp/doco_test_tokens.json verify \
  --token "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## Recommended Approach

For production N8N workflows, we recommend:

1. **Use HTTP Request node** instead of MCP Client
2. **Port 8010** (Web API) instead of Port 8011 (MCP)
3. **REST endpoints** are more stable in N8N
4. **MCP protocol** is better suited for AI assistants (Claude, etc.)

The Web API provides the same functionality with better N8N compatibility.

## Summary

**If you get "Error in sub-node 'MCP DOCO Client'":**

1. ✅ Switch to HTTP Request node (recommended)
2. ✅ Use Web API on port 8010
3. ✅ Pass token in Authorization header
4. ✅ See `docs/N8N_INTEGRATION.md` for full HTTP examples

The MCP endpoint works perfectly with proper MCP clients (like Python mcp library, Claude Desktop, etc.) but N8N's MCP Client node may have compatibility issues.
