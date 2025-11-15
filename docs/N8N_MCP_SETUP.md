# N8N MCP Client Setup for doco

## Quick Start: Connect N8N to doco MCP Server

Your doco MCP server is running on **Streamable HTTP** which is fully compatible with N8N's MCP Client Tool!

### Prerequisites

✅ doco MCP server running on `localhost:8011`  
✅ Bearer token: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss`  
✅ N8N instance running

## Step-by-Step Setup

### Step 1: Add MCP Client Node to N8N

1. Open your N8N workflow
2. Add node: Search for "**MCP Client Tool**" or "**MCP**"
3. Add the node to your workflow

### Step 2: Configure MCP Server Connection

In the MCP Client Tool node settings:

**Server Configuration:**
- **URL**: `http://localhost:8011/mcp/` (or `http://doco_dev:8011/mcp/` if in Docker network)
- **Transport**: Streamable HTTP (automatic)
- **Authentication**: Custom Headers (see below)

**Authentication Headers:**
Add custom header for token authentication:
- **Header Name**: `Authorization`
- **Header Value**: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss`

> **Note**: If your N8N MCP Client doesn't support custom headers, you'll need to pass the token in the tool arguments (see below).

### Step 3: Test Connection

The MCP Client should automatically discover these tools:
- ✅ `ping` - Health check
- ✅ `render_graph` - Generate charts
- ✅ `get_image` - Retrieve saved images

### Step 4: Use the Tools

#### Example 1: Simple Chart Generation

**Tool**: `render_graph`

**Arguments**:
```json
{
  "title": "Monthly Sales",
  "x": [1, 2, 3, 4, 5],
  "y": [1200, 1900, 1500, 2100, 1800],
  "type": "bar",
  "format": "png",
  "theme": "light",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss"
}
```

**Response**: Binary image data (PNG) with MIME type `image/png`

#### Example 2: Dynamic Data from Previous Node

**Tool**: `render_graph`

**Arguments** (using N8N expressions):
```json
{
  "title": "{{ $json.chartTitle }}",
  "x": {{ $json.xData }},
  "y": {{ $json.yData }},
  "type": "{{ $json.chartType }}",
  "format": "png",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss"
}
```

#### Example 3: Proxy Mode (Save & Retrieve)

**Step 1 - Generate and Save:**

**Tool**: `render_graph`

**Arguments**:
```json
{
  "title": "Report Chart",
  "x": [1, 2, 3, 4, 5],
  "y": [10, 25, 15, 30, 20],
  "type": "line",
  "format": "png",
  "proxy": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss"
}
```

**Response**: 
```json
{
  "guid": "550e8400-e29b-41d4-a716-446655440000",
  "format": "png"
}
```

**Step 2 - Retrieve Later:**

**Tool**: `get_image`

**Arguments**:
```json
{
  "guid": "550e8400-e29b-41d4-a716-446655440000",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss"
}
```

**Response**: Binary image data

#### Example 4: Health Check

**Tool**: `ping`

**Arguments**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss"
}
```

**Response**:
```
Server is running
Timestamp: 2025-11-12T13:01:38.336074
Service: doco
```

## Available Chart Types

- `line` - Line chart with optional markers
- `bar` - Vertical bar chart
- `scatter` - Scatter plot

## Available Themes

- `light` - Light background (default)
- `dark` - Dark background
- `bizlight` - Business light theme
- `bizdark` - Business dark theme

## Available Formats

- `png` - PNG image (default, recommended)
- `jpg` - JPEG image
- `svg` - SVG vector graphics (scalable)
- `pdf` - PDF document

## Advanced Parameters

All optional parameters for `render_graph`:

```json
{
  "title": "Chart Title",
  "x": [1, 2, 3, 4, 5],
  "y": [10, 20, 30, 40, 50],
  "type": "line",
  "format": "png",
  "theme": "light",
  "grid": true,
  "legend": true,
  "xlabel": "Time (hours)",
  "ylabel": "Temperature (°C)",
  "color": "#FF5733",
  "alpha": 0.8,
  "linewidth": 2,
  "marker": "o",
  "markersize": 8,
  "proxy": false,
  "token": "..."
}
```

## Example N8N Workflows

### Workflow 1: Database → Chart → Email

```
[Schedule] → [MySQL Query] → [Function: Format Data] → [MCP: render_graph] → [Send Email]
```

**Function Node (Format Data)**:
```javascript
const rows = $input.all();
return {
  json: {
    chartTitle: "Daily Sales",
    xData: rows.map(r => r.day),
    yData: rows.map(r => r.sales),
    chartType: "bar"
  }
};
```

### Workflow 2: Webhook → Multi-Chart → Slack

```
[Webhook] → [Split Into Batches] → [MCP: render_graph] → [Merge] → [Slack: Send Files]
```

### Workflow 3: API → Chart → Cloud Storage

```
[HTTP Request: Fetch API] → [MCP: render_graph (proxy)] → [Save GUID] → [Later: get_image] → [S3 Upload]
```

## Troubleshooting

### Connection Failed
**Issue**: Cannot connect to MCP server

**Solutions**:
- ✅ Verify doco MCP server is running: `curl http://localhost:8011/mcp/ping`
- ✅ Check N8N can reach the server (same network if using Docker)
- ✅ Use correct URL: `http://localhost:8011/mcp/` (note trailing slash)

### 401 Unauthorized
**Issue**: Authentication failed

**Solutions**:
- ✅ Include token in arguments: `"token": "eyJhbG..."`
- ✅ Verify token hasn't expired
- ✅ Check JWT secret matches between servers

### Tool Not Found
**Issue**: MCP Client doesn't show doco tools

**Solutions**:
- ✅ Test connection with ping first
- ✅ Refresh/reinitialize the MCP connection
- ✅ Check MCP server logs for errors

### Invalid Arguments
**Issue**: 422 Validation Error

**Solutions**:
- ✅ Ensure `x` and `y` are arrays of numbers
- ✅ Check arrays are same length
- ✅ Verify `type` is one of: line, bar, scatter
- ✅ Validate numeric parameters (alpha: 0-1, linewidth > 0)

### Empty/Corrupted Image
**Issue**: Image data is empty or invalid

**Solutions**:
- ✅ Check server logs for matplotlib errors
- ✅ Verify data arrays contain valid numbers (not NaN/Infinity)
- ✅ Try different format (png vs svg)

## Performance Tips

1. **Use Proxy Mode** for large images or repeated access
2. **SVG format** for charts that need scaling
3. **PNG format** for final output (best compatibility)
4. **Batch requests** when generating multiple charts
5. **Cache GUIDs** when using proxy mode

## Security Best Practices

1. **Store token securely** in N8N credentials/environment variables
2. **Use HTTPS** in production environments
3. **Rotate tokens** before expiry (current expires: Nov 11, 2026)
4. **Group isolation**: Each token's group can only access its own images
5. **Network isolation**: Run in private Docker network when possible

## Testing Your Setup

Run this test command to verify MCP server is accessible:

```bash
python -c "
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def test():
    async with streamablehttp_client('http://localhost:8011/mcp/') as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            tools = await session.list_tools()
            print('✓ MCP Server OK')
            print(f'  Tools: {[t.name for t in tools.tools]}')

asyncio.run(test())
"
```

Expected output:
```
✓ MCP Server OK
  Tools: ['ping', 'render_graph', 'get_image']
```

## Next Steps

- 📚 See `AUTHENTICATION.md` for configuration details
- 🎨 See `THEMES.md` for theme customization
- 🔐 See `TEST_AUTH.md` for authentication details
- 💾 See `PROXY_MODE.md` for persistent storage details
- 📖 See `README_N8N_MCP.md` for architecture overview

## Getting Help

Example implementations:
- `test/mcp/manual_test_mcp_server.py` - Python MCP client example
- `test/web/manual_test_web_server.py` - HTTP REST example
- `docs/MCP_README.md` - MCP protocol details
