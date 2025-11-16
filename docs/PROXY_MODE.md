# Proxy Mode Feature Documentation

## Overview

Proxy Mode is a new feature that allows document rendering to store rendered documents on the server instead of transmitting them over the network. This is useful for large documents (especially PDFs) where transmitting the full content would be expensive or inefficient.

## How It Works

### Basic Flow

1. **Client requests document with proxy=true**:
   ```json
   {
     "session_id": "...",
     "format": "pdf",
     "proxy": true
   }
   ```

2. **Server renders and stores the document**:
   - Renders the document normally
   - Stores it in `data/proxy/{group}/{proxy_guid}.json`
   - Returns only the GUID to the client

3. **Server response**:
   ```json
   {
     "status": "success",
     "data": {
       "proxy_guid": "550e8400-e29b-41d4-a716-446655440000",
       "format": "pdf",
       "content": "",
       "message": "Document stored in proxy mode"
     }
   }
   ```

4. **Client retrieves document later** (future enhancement):
   ```json
   {
     "proxy_guid": "550e8400-e29b-41d4-a716-446655440000"
   }
   ```

## Implementation Details

### MCP Tool: `get_document`

The existing `get_document` tool has been enhanced with a new `proxy` parameter:

```json
{
  "name": "get_document",
  "parameters": {
    "proxy": {
      "type": "boolean",
      "description": "If true, store rendered document on server and return proxy_guid instead of content. Useful for large documents to avoid transmission overhead."
    }
  }
}
```

### Storage Structure

Proxy documents are stored in a segregated directory structure:

```
data/proxy/
├── public/
│   ├── 550e8400-e29b-41d4-a716-446655440000.json
│   ├── 660e8400-e29b-41d4-a716-446655440001.json
│   └── ...
├── private/
│   ├── 770e8400-e29b-41d4-a716-446655440002.json
│   └── ...
└── ...
```

Each file contains document metadata:

```json
{
  "proxy_guid": "550e8400-e29b-41d4-a716-446655440000",
  "format": "pdf",
  "content": "base64-encoded-or-html-content",
  "created_at": "2025-11-16T14:07:10.327Z"
}
```

### Code Changes

#### 1. Data Models (`app/validation/document_models.py`)

**GetDocumentInput** - Added proxy parameter:
```python
class GetDocumentInput:
    session_id: str
    format: str
    style_id: Optional[str] = None
    proxy: Optional[bool] = False  # NEW
```

**GetDocumentOutput** - Added proxy_guid field:
```python
class GetDocumentOutput:
    status: str
    format: OutputFormat
    content: str
    proxy_guid: Optional[str] = None  # NEW
```

**New Models**:
- `GetProxyDocumentInput` - Input for retrieving proxy documents
- `GetProxyDocumentOutput` - Output with cached document content

#### 2. Configuration (`app/config.py`)

Added proxy directory management:

```python
@classmethod
def get_proxy_dir(cls) -> Path:
    """Get the directory for proxy-stored rendered documents."""
    return cls.get_data_dir() / "proxy"

def get_default_proxy_dir() -> str:
    """Get default proxy directory as string."""
    return str(Config.get_proxy_dir())
```

#### 3. Rendering Engine (`app/rendering/engine.py`)

Enhanced to support proxy storage:

```python
async def render_document(
    self,
    session: Session,
    output_format: OutputFormat,
    style_id: Optional[str] = None,
    proxy: bool = False  # NEW
) -> GetDocumentOutput:
    # ... render document ...
    
    if proxy:
        proxy_guid = await self._store_proxy_document(content, session.group, output_format)
        content = ""  # Clear content to avoid transmission
    
    return GetDocumentOutput(
        status="success",
        format=output_format,
        content=content,
        proxy_guid=proxy_guid if proxy else None
    )

async def _store_proxy_document(
    self, 
    content: str, 
    group: str, 
    output_format: OutputFormat
) -> str:
    """Store rendered document and return GUID."""
    # Creates directory if needed
    # Generates UUID
    # Saves as JSON with metadata
    # Returns proxy_guid

async def get_proxy_document(
    self,
    proxy_guid: str,
    group: str
) -> GetProxyDocumentOutput:
    """Retrieve previously stored proxy document."""
    # Loads from disk
    # Validates format
    # Returns GetProxyDocumentOutput
```

#### 4. MCP Server (`app/mcp_server.py`)

Updated `get_document` tool to support proxy:

```python
# Tool schema now includes proxy parameter
"proxy": {
    "type": "boolean",
    "description": "If true, store rendered document on server..."
}

# Handler passes proxy flag to renderer
output = await renderer.render_document(
    session=session,
    output_format=OutputFormat(format_value),
    style_id=payload.style_id,
    proxy=payload.proxy  # NEW
)
```

## Benefits

1. **Reduced Network Overhead**: Large documents (especially PDFs) don't need to be base64-encoded and transmitted
2. **Server-Side Storage**: Documents available for later retrieval without client-side storage
3. **Group Segregation**: Documents are organized by group for security and organization
4. **Backward Compatible**: Existing code works unchanged; proxy mode is optional

## Testing

Comprehensive test suite (`test/mcp/test_proxy_rendering.py`) covers:

- ✅ Proxy mode returns GUID instead of content
- ✅ Proxy documents can be retrieved by GUID
- ✅ Proxy mode works with different formats (HTML, PDF, Markdown)
- ✅ Error handling for non-existent documents
- ✅ Regular rendering still works (backward compatibility)
- ✅ Documents segregated by group
- ✅ Multiple documents stored independently

**Test Results**: 7/7 passing ✅

## Future Enhancements

1. **Add `get_proxy_document` MCP Tool**: New tool to retrieve stored documents
2. **Add Cleanup Mechanism**: Auto-expire old proxy documents (configurable TTL)
3. **Add Proxy Limits**: Limit size and number of proxy documents per group
4. **Add Monitoring**: Track proxy storage usage and performance

## Usage Example

```python
# Request proxy mode rendering
response = client.call_tool(
    "get_document",
    {
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "format": "pdf",
        "proxy": True  # Enable proxy mode
    }
)

# Returns lightweight response with GUID
print(response["data"]["proxy_guid"])
# Output: "550e8400-e29b-41d4-a716-446655440000"

# Later, retrieve the document (when get_proxy_document tool is added)
# response = client.call_tool(
#     "get_proxy_document",
#     {"proxy_guid": "550e8400-e29b-41d4-a716-446655440000"}
# )
# Document content is transmitted only when explicitly requested
```

## Configuration

Proxy storage location can be configured via Config class:

```python
# Override default location
proxy_dir = Config.get_proxy_dir()

# Or use convenience function
from app.config import get_default_proxy_dir
proxy_path = get_default_proxy_dir()  # "data/proxy"
```

## Backward Compatibility

All existing code continues to work unchanged:

- Default `proxy=False` maintains original behavior
- Content is returned in response when proxy mode not requested
- No breaking changes to any MCP tools or APIs
- Full test suite validation: **250/250 tests passing** ✅
