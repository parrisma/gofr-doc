# N8N MCP Integration

## Overview

This document explains how N8N interacts with MCP (Model Context Protocol) servers and the limitations of the current setup.

## N8N MCP Capabilities

### 1. N8N as MCP Server (Supported)
N8N can act as an **MCP Server**, exposing n8n workflows and tools to external MCP clients.

**Transport:** SSE (Server-Sent Events) and streamable HTTP  
**Configuration:** Use the "MCP Server Trigger" node in n8n workflows  
**Access:** External clients can connect to n8n's MCP endpoints via HTTP

Example workflow:
1. Create a workflow with "MCP Server Trigger" node
2. Add n8n tool nodes (HTTP Request, Code, etc.)
3. Activate the workflow
4. External MCP clients can call these tools via SSE/HTTP

### 2. N8N as MCP Client (Limited Support)
N8N can act as an **MCP Client**, connecting to external MCP servers to use their tools.

**Important Limitation:** N8N's MCP Client Tool node **only supports SSE/HTTP transport**, NOT stdio transport.

This means:
- ✅ N8N can connect to SSE-based MCP servers (like n8n itself)
- ❌ N8N **cannot directly** connect to stdio-based MCP servers (like doco)

## Connecting N8N to doco MCP Server

The doco MCP server uses **Streamable HTTP transport** on port 8011, which is the modern preferred standard for MCP servers (superseding SSE). This makes it fully compatible with N8N's MCP Client Tool!

### Option 1: Use N8N's MCP Client Tool (Recommended for MCP Protocol)
N8N can connect directly to doco's Streamable HTTP MCP endpoint:

**Configuration:**
1. Add "MCP Client Tool" node to your n8n workflow
2. Configure the endpoint:
   - URL: `http://doco_dev:8011/mcp` (dev) or `http://doco_prod:8011/mcp` (prod)
   - Authentication: None (if running on doco_net network)
3. Use the `render_graph` or `ping` tools via MCP protocol

**Example MCP Tool Call (Normal Mode):**
```json
{
  "tool": "render_graph",
  "arguments": {
    "x": [1, 2, 3, 4, 5],
    "y": [2, 4, 6, 8, 10],
    "title": "Sales Data",
    "type": "line",
    "theme": "dark"
  }
}
```

Returns base64-encoded image data directly.

**Example MCP Tool Call (Proxy Mode):**
```json
{
  "tool": "render_graph",
  "arguments": {
    "x": [1, 2, 3, 4, 5],
    "y": [2, 4, 6, 8, 10],
    "title": "Sales Data",
    "type": "line",
    "format": "png",
    "proxy": true
  }
}
```

Returns a GUID string. The image is saved to `/tmp/doco_images/{guid}.png` on the server. You can retrieve it later using the `get_image` tool or access it via web endpoints:
- MCP: `get_image` tool with the GUID
- Web: `GET http://doco_dev:8010/render/{guid}`
- Browser: `GET http://doco_dev:8010/render/{guid}/html`

**Proxy Mode Benefits:**
- Reduces network bandwidth (only GUID transferred initially)
- Persistent storage of rendered graphs
- Enables deferred retrieval and multiple access patterns
- Ideal for large images or when images need to be reused

### Option 2: Use N8N's HTTP Request Node (Alternative)
Instead of using MCP protocol, call doco's REST API directly:

```json
{
  "method": "POST",
  "url": "http://doco_dev:8010/render",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "x": [1, 2, 3],
    "y": [4, 5, 6],
    "title": "My Graph"
  }
}
```

This is the **recommended approach** for the current setup.

### Option 3: Use mcp-remote Gateway (For External Clients)
External tools like Claude Desktop can use `mcp-remote` to bridge stdio MCP servers to SSE:

```json
{
  "mcpServers": {
    "doco": {
      "command": "npx",
      "args": [
        "mcp-remote",
  "http://localhost:8011/mcp",
        "--stdio"
      ]
    }
  }
}
```

However, this is for external clients connecting to n8n or other services, not for n8n itself.

### Current Setup

### Docker Network: doco_net
Both doco and n8n containers run on the same Docker network:
- **doco_dev/prod REST API:** Accessible at `http://doco_dev:8010` or `http://doco_prod:8010`
- **doco_dev/prod MCP Streamable HTTP:** Accessible at `http://doco_dev:8011/mcp` or `http://doco_prod:8011/mcp`
- **n8n:** Accessible at `http://n8n:5678`

### Communication Pattern
```
┌─────────────┐  MCP Streamable HTTP (8011)  ┌────────────┐
│   N8N       │ ────────────────────────►    │   doco    │
│ Workflows   │     HTTP REST (Port 8010)    │  Service   │
│             │ ────────────────────────►    │            │
└─────────────┘                              └────────────┘
     │                                            │
     │                                            │
     └────────── doco_net Network ────────────────┘
```

### Recommended Usage in N8N

1. **Add HTTP Request Node** to your n8n workflow
2. **Configure:**
   - Method: POST
  - URL: `http://doco_dev:8010/render` (dev) or `http://doco_prod:8010/render` (prod)
   - Body: JSON with graph parameters

3. **Example Request:**
```json
{
  "x": [1, 2, 3, 4, 5],
  "y": [2, 4, 6, 8, 10],
  "title": "Sales Data",
  "type": "line",
  "format": "png",
  "theme": "dark"
}
```

4. **Handle Response:**
   - Success: Binary image data (base64 encoded)
   - Error: JSON with error message

## Environment Variables

None required for basic doco + n8n communication via HTTP.

If you want n8n to act as an MCP Server (for external clients):
- Configure authentication in n8n's MCP Server Trigger node
- Expose n8n's port 5678 externally
- Configure reverse proxy with SSE support (disable buffering)

## Summary

- **N8N → doco (MCP):** Use MCP Client Tool node to connect to `http://doco_dev:8011/mcp` ✅
- **N8N → doco (REST):** Use HTTP Request node to call `http://doco_dev:8010/render` ✅
- **N8N as MCP Server:** Supported via Streamable HTTP (for exposing n8n workflows to external MCP clients) ✅
- **N8N as MCP Client:** Fully supported - doco uses Streamable HTTP transport! ✅
- **doco MCP Server:** Accessible via Streamable HTTP on port 8011, compatible with N8N's MCP Client Tool ✅
- **Transport:** Streamable HTTP (modern MCP standard, superseding SSE) ✅

You can choose between:
1. **MCP Protocol (Port 8011):** Full MCP tool integration with standardized Streamable HTTP protocol
2. **HTTP REST API (Port 8010):** Simple HTTP endpoint for direct rendering requests

Both approaches work seamlessly within the doco_net Docker network.
