# N8N MCP Client Setup for doco

## Quick Start: Connect N8N to doco MCP Server

Your doco MCP server is running on **Streamable HTTP** which is fully compatible with N8N's MCP Client Tool!

### Prerequisites

✅ doco MCP server running on `localhost:8011`  
✅ Bearer token: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJncm91cCI6Im44biIsImlhdCI6MTc2Mjg4MTI1MSwiZXhwIjoxNzk0NDE3MjUxfQ.Zj2ZLtYmZ5jT579pSB_mHjVqUmhR1xQh6Hx4pqqp6ss`  
## Step 3: Test Connection

The MCP Client should automatically discover available tools:
- ✅ `ping` - Health check

## Next Steps

- 📚 See `AUTHENTICATION.md` for configuration details

## Getting Help

Example implementations:
- `test/mcp/manual_test_mcp_server.py` - Python MCP client example
- `test/web/manual_test_web_server.py` - HTTP REST example
- `docs/MCP_README.md` - MCP protocol details
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
