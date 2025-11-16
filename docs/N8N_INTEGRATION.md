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

## Method 2: MCP Protocol Integration

### Setup MCP Server Connection

1. **Install MCP support in N8N** (if available)

2. **Configure MCP Server:**
   - **URL**: `http://localhost:8011/mcp/`
   - **Protocol**: HTTP Streamable

3. **Available Tools:**
   - `ping` - Health check

## Next Steps

- See `docs/TEST_AUTH.md` for authentication details
- See `docs/AUTHENTICATION.md` for configuration details

## Getting Help

Check the test files for working examples:
- `test/web/manual_test_web_server.py`
- `test/mcp/manual_test_mcp_server.py`
