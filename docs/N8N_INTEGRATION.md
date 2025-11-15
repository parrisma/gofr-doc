# N8N Integration Guide

This guide shows how to integrate doco with N8N for automated chart generation.

## Prerequisites

- doco MCP or Web server running
- N8N instance running
- Valid bearer token for authentication

## Your Bearer Token

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss
```

- **Group**: n8n
- **Expires**: November 11, 2026

## Method 1: HTTP Request Node (Recommended)

### Setup Steps

1. **Add HTTP Request Node** to your workflow

2. **Configure the node:**
   - **Method**: POST
  - **URL**: `http://localhost:8010/render`
   - **Authentication**: Generic Credential Type
   - **Header Auth**:
     - Name: `Authorization`
     - Value: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss`

3. **Body (JSON)**:
```json
{
  "title": "My Chart",
  "x": [1, 2, 3, 4, 5],
  "y": [10, 25, 15, 30, 20],
  "type": "bar",
  "format": "png",
  "theme": "light"
}
```

4. **Response Options**:
   - Response Format: JSON
   - The response contains `image_data` (base64 encoded) and `format`

### Dynamic Data Example

Use expressions to pass dynamic data from previous nodes:

```json
{
  "title": "{{ $json.chartTitle }}",
  "x": {{ $json.xValues }},
  "y": {{ $json.yValues }},
  "type": "{{ $json.chartType }}",
  "format": "png"
}
```

### Chart Types

- `line` - Line chart
- `bar` - Bar chart
- `scatter` - Scatter plot

### Themes

- `light` - Light theme (default)
- `dark` - Dark theme
- `bizlight` - Business light theme
- `bizdark` - Business dark theme

### Formats

- `png` - PNG image (recommended)
- `jpg` - JPEG image
- `svg` - SVG vector
- `pdf` - PDF document

## Method 2: MCP Protocol Integration

### Setup MCP Server Connection

1. **Install MCP support in N8N** (if available)

2. **Configure MCP Server:**
   - **URL**: `http://localhost:8011/mcp/`
   - **Protocol**: HTTP Streamable

3. **Available Tools:**
   - `ping` - Health check
   - `render_graph` - Generate charts
   - `get_image` - Retrieve saved images

### Using render_graph Tool

**Input Schema:**
```json
{
  "title": "Chart Title",
  "x": [1, 2, 3, 4, 5],
  "y": [10, 20, 30, 40, 50],
  "type": "line",
  "format": "png",
  "theme": "light",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
- Binary image data with MIME type (e.g., `image/png`)

### Using get_image Tool

Retrieve previously generated images:

```json
{
  "guid": "550e8400-e29b-41d4-a716-446655440000",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

## Method 3: Proxy Mode (Save & Retrieve)

For workflows that need to save and retrieve charts:

1. **Generate chart with proxy=true:**
```json
{
  "title": "My Chart",
  "x": [1, 2, 3],
  "y": [10, 20, 30],
  "type": "bar",
  "proxy": true,
  "token": "..."
}
```

**Response:**
```json
{
  "guid": "550e8400-e29b-41d4-a716-446655440000",
  "format": "png"
}
```

2. **Retrieve later using the GUID:**
  - **URL**: `http://localhost:8010/image/{guid}`
   - **Method**: GET
   - **Header**: `Authorization: Bearer {token}`

## Example Workflows

### Simple Bar Chart

```
[Trigger] → [Set Data] → [HTTP Request (doco)] → [Save to Storage]
```

### Dynamic Chart from Database

```
[Schedule] → [Database Query] → [Function (format data)] → [HTTP Request (doco)] → [Send Email with Chart]
```

### Multi-Chart Dashboard

```
[Trigger] → [Split Data] → [HTTP Request (doco)] × 3 → [Merge Images] → [Upload to Cloud]
```

## Troubleshooting

### 401 Unauthorized
- Check token is included in Authorization header
- Verify token hasn't expired
- Ensure server is using the same JWT secret

### 422 Validation Error
- Check data types (arrays must be arrays, not strings)
- Ensure x and y arrays are same length
- Verify chart type is valid

### Connection Refused
- Ensure doco server is running
- Check correct port (8010 for Web, 8011 for MCP)
- Verify network connectivity

## Advanced Configuration

### Custom Styling

```json
{
  "title": "Custom Styled Chart",
  "x": [1, 2, 3, 4, 5],
  "y": [10, 25, 15, 30, 20],
  "type": "line",
  "grid": true,
  "legend": true,
  "alpha": 0.8,
  "marker": "o",
  "markersize": 8,
  "linewidth": 2,
  "color": "#FF5733"
}
```

### SVG for Scaling

Use SVG format for charts that need to scale:

```json
{
  "format": "svg",
  ...
}
```

SVG images can be resized without quality loss.

## Security Notes

1. **Token Storage**: Store tokens securely in N8N credentials
2. **HTTPS**: Use HTTPS in production
3. **Token Rotation**: Refresh tokens before expiry
4. **Group Isolation**: Each token's group can only access its own images

## Next Steps

- See `docs/TEST_AUTH.md` for authentication details
- See `docs/PROXY_MODE.md` for GUID-based retrieval
- See `docs/THEMES.md` for styling options
- See `docs/AUTHENTICATION.md` for configuration details

## Getting Help

Check the test files for working examples:
- `test/web/manual_test_web_server.py`
- `test/mcp/manual_test_mcp_server.py`
