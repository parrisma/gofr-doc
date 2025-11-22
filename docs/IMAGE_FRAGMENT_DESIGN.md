# Image Fragment Design - URL-based Images with Validation

## Overview
New MCP tool `add_image_fragment` for adding validated URL-based images to documents with format-specific rendering (embedded for PDF/HTML, linked for Markdown).

## Tool Specification

### Tool Name
`add_image_fragment`

### Description
Add an image from a URL to the document. **URL is validated immediately** when added (not at render time). Images are embedded in PDF/HTML or linked in Markdown based on output format.

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "session_id": {
      "type": "string",
      "description": "Session identifier from create_document_session"
    },
    "image_url": {
      "type": "string",
      "description": "URL of the image to download and display. VALIDATED IMMEDIATELY when added. Must be accessible and return valid image content-type (image/png, image/jpeg, image/gif, image/webp, image/svg+xml)."
    },
    "title": {
      "type": "string",
      "description": "Optional title/caption displayed above the image"
    },
    "width": {
      "type": "integer",
      "description": "Target width in pixels. If only width specified, height scales proportionally."
    },
    "height": {
      "type": "integer",
      "description": "Target height in pixels. If only height specified, width scales proportionally."
    },
    "alt_text": {
      "type": "string",
      "description": "Alternative text for accessibility. Defaults to title or 'Image'."
    },
    "alignment": {
      "type": "string",
      "enum": ["left", "center", "right"],
      "description": "Image alignment. Default: center"
    },
    "require_https": {
      "type": "boolean",
      "description": "If true, only HTTPS URLs allowed. If false, HTTP URLs permitted. Default: true for security."
    },
    "position": {
      "type": "string",
      "description": "Where to insert: 'end' (default), 'start', 'before:<guid>', 'after:<guid>'"
    }
  },
  "required": ["session_id", "image_url"]
}
```

## URL Validation (At Add Time)

### Validation Steps
1. **Scheme validation** - Check protocol (https:// or http:// if require_https=false)
2. **URL format validation** - Parse URL to ensure well-formed
3. **HEAD request** - Validate URL is accessible (200 OK response)
4. **Content-Type validation** - Check Content-Type header matches allowed types
5. **Size check (optional)** - Reject images > configurable max size (e.g., 10MB)

### Allowed Content-Types
- `image/png`
- `image/jpeg`
- `image/jpg`
- `image/gif`
- `image/webp`
- `image/svg+xml`

### Error Responses

```python
# Invalid scheme
{
  "status": "error",
  "error_code": "INVALID_IMAGE_URL",
  "message": "Image URL must use HTTPS protocol (require_https=true)",
  "recovery": "Use an HTTPS URL or set require_https=false if HTTP is acceptable",
  "details": {
    "url": "http://example.com/image.png",
    "reason": "Non-HTTPS URL with require_https=true"
  }
}

# URL not accessible
{
  "status": "error",
  "error_code": "IMAGE_URL_NOT_ACCESSIBLE",
  "message": "Image URL returned HTTP 404 Not Found",
  "recovery": "Verify the URL is correct and accessible. Test it in a browser.",
  "details": {
    "url": "https://example.com/missing.png",
    "status_code": 404,
    "reason": "HTTP 404 Not Found"
  }
}

# Invalid content-type
{
  "status": "error",
  "error_code": "INVALID_IMAGE_CONTENT_TYPE",
  "message": "URL does not return a valid image content-type",
  "recovery": "Ensure the URL points to an image file. Allowed types: image/png, image/jpeg, image/gif, image/webp, image/svg+xml",
  "details": {
    "url": "https://example.com/document.pdf",
    "content_type": "application/pdf",
    "allowed_types": ["image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"]
  }
}

# Timeout
{
  "status": "error",
  "error_code": "IMAGE_URL_TIMEOUT",
  "message": "Image URL validation timed out after 10 seconds",
  "recovery": "Check if the URL is slow or unreachable. Try a different URL or ensure network connectivity.",
  "details": {
    "url": "https://slow-server.com/image.png",
    "timeout_seconds": 10
  }
}

# Image too large
{
  "status": "error",
  "error_code": "IMAGE_TOO_LARGE",
  "message": "Image size exceeds maximum allowed size",
  "recovery": "Use a smaller image or compress the image before uploading",
  "details": {
    "url": "https://example.com/huge.png",
    "content_length": 15728640,
    "max_size_bytes": 10485760,
    "max_size_mb": 10
  }
}
```

## Format-Specific Rendering

### PDF Rendering
- **Download image** from validated URL at render time
- **Embed image data** in PDF using base64 encoding
- Apply width/height scaling
- Include title as caption
- Result: Self-contained PDF with embedded images

### HTML Rendering
- **Download image** from validated URL at render time
- **Embed image data** using data URI (base64)
- Apply width/height attributes and CSS styling
- Include title as caption in `<div class="image-title">`
- Result: Self-contained HTML with embedded images

### Markdown Rendering
- **Link to URL** directly (no download at render time)
- Use standard markdown image syntax: `![alt_text](image_url "title")`
- Include width/height as HTML attributes if specified: `<img src="..." width="X" height="Y">`
- Result: Lightweight markdown that references external URLs

## Implementation Details

### Storage in Session
```json
{
  "fragment_type": "image_from_url",
  "fragment_instance_guid": "550e8400-e29b-41d4-a716-446655440000",
  "parameters": {
    "image_url": "https://example.com/chart.png",
    "title": "Q4 Sales Performance",
    "width": 800,
    "height": null,
    "alt_text": "Bar chart showing quarterly sales data",
    "alignment": "center",
    "require_https": true,
    "validated_at": "2025-11-22T15:30:00Z",
    "content_type": "image/png",
    "content_length": 524288
  },
  "created_at": "2025-11-22T15:30:00Z",
  "position": 3
}
```

### Validation Service

```python
# app/validation/image_validator.py

import httpx
from typing import Tuple, Optional
from dataclasses import dataclass

@dataclass
class ImageValidationResult:
    valid: bool
    url: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    content_type: Optional[str] = None
    content_length: Optional[int] = None
    details: Optional[dict] = None

class ImageURLValidator:
    """Validates image URLs at add time (not render time)"""
    
    ALLOWED_CONTENT_TYPES = {
        'image/png',
        'image/jpeg',
        'image/jpg',
        'image/gif',
        'image/webp',
        'image/svg+xml'
    }
    
    DEFAULT_MAX_SIZE_MB = 10
    DEFAULT_TIMEOUT_SECONDS = 10
    
    def __init__(
        self,
        max_size_mb: int = DEFAULT_MAX_SIZE_MB,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    ):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.timeout_seconds = timeout_seconds
    
    async def validate_image_url(
        self,
        url: str,
        require_https: bool = True
    ) -> ImageValidationResult:
        """Validate image URL and return detailed result"""
        
        # 1. Scheme validation
        if require_https and not url.startswith('https://'):
            return ImageValidationResult(
                valid=False,
                url=url,
                error_code='INVALID_IMAGE_URL',
                error_message='Image URL must use HTTPS protocol (require_https=true)',
                details={'reason': 'Non-HTTPS URL with require_https=true'}
            )
        
        if not url.startswith(('http://', 'https://')):
            return ImageValidationResult(
                valid=False,
                url=url,
                error_code='INVALID_IMAGE_URL',
                error_message='Image URL must use HTTP or HTTPS protocol',
                details={'reason': 'Invalid URL scheme'}
            )
        
        # 2. URL format validation (httpx will validate)
        try:
            # 3. HEAD request to validate accessibility
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.head(url, follow_redirects=True)
                
                # Check status code
                if response.status_code != 200:
                    return ImageValidationResult(
                        valid=False,
                        url=url,
                        error_code='IMAGE_URL_NOT_ACCESSIBLE',
                        error_message=f'Image URL returned HTTP {response.status_code}',
                        details={
                            'status_code': response.status_code,
                            'reason': f'HTTP {response.status_code}'
                        }
                    )
                
                # 4. Content-Type validation
                content_type = response.headers.get('content-type', '').split(';')[0].strip().lower()
                if content_type not in self.ALLOWED_CONTENT_TYPES:
                    return ImageValidationResult(
                        valid=False,
                        url=url,
                        error_code='INVALID_IMAGE_CONTENT_TYPE',
                        error_message='URL does not return a valid image content-type',
                        content_type=content_type,
                        details={
                            'content_type': content_type,
                            'allowed_types': list(self.ALLOWED_CONTENT_TYPES)
                        }
                    )
                
                # 5. Size check
                content_length = response.headers.get('content-length')
                if content_length:
                    content_length = int(content_length)
                    if content_length > self.max_size_bytes:
                        return ImageValidationResult(
                            valid=False,
                            url=url,
                            error_code='IMAGE_TOO_LARGE',
                            error_message='Image size exceeds maximum allowed size',
                            content_type=content_type,
                            content_length=content_length,
                            details={
                                'content_length': content_length,
                                'max_size_bytes': self.max_size_bytes,
                                'max_size_mb': self.max_size_bytes / (1024 * 1024)
                            }
                        )
                
                # Success
                return ImageValidationResult(
                    valid=True,
                    url=url,
                    content_type=content_type,
                    content_length=content_length
                )
        
        except httpx.TimeoutException:
            return ImageValidationResult(
                valid=False,
                url=url,
                error_code='IMAGE_URL_TIMEOUT',
                error_message=f'Image URL validation timed out after {self.timeout_seconds} seconds',
                details={'timeout_seconds': self.timeout_seconds}
            )
        
        except httpx.HTTPError as exc:
            return ImageValidationResult(
                valid=False,
                url=url,
                error_code='IMAGE_URL_ERROR',
                error_message=f'Error accessing image URL: {str(exc)}',
                details={'error': str(exc)}
            )
        
        except Exception as exc:
            return ImageValidationResult(
                valid=False,
                url=url,
                error_code='IMAGE_VALIDATION_ERROR',
                error_message=f'Unexpected error validating image URL: {str(exc)}',
                details={'error': str(exc)}
            )
```

### MCP Tool Handler

```python
# In app/mcp_server.py

async def _tool_add_image_fragment(arguments: Dict[str, Any]) -> ToolResponse:
    """Add a validated image fragment from URL to document session.
    
    SECURITY: Validates session belongs to caller's group.
    VALIDATION: Validates URL is accessible and returns valid image content-type
                at add time (not render time).
    
    Args:
        arguments: Dict containing session_id, image_url, optional parameters
    
    Returns:
        ToolResponse with success (including fragment_instance_guid) or detailed error
    """
    from app.validation.image_validator import ImageURLValidator
    
    # Parse and validate input
    payload = AddImageFragmentInput.model_validate(arguments)
    manager = _ensure_manager()
    caller_group = payload.group if hasattr(payload, "group") else "public"
    
    # SECURITY: Verify session belongs to caller's group
    session = await manager.get_session(payload.session_id)
    if session is None or session.group != caller_group:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery="Verify the session_id is correct. Call list_active_sessions to see your sessions.",
        )
    
    # VALIDATION: Validate image URL
    validator = ImageURLValidator()
    validation_result = await validator.validate_image_url(
        url=payload.image_url,
        require_https=payload.require_https
    )
    
    if not validation_result.valid:
        return _error(
            code=validation_result.error_code,
            message=validation_result.error_message,
            recovery=validation_result.details.get('recovery', 'Check the URL and try again'),
            details=validation_result.details
        )
    
    # Build fragment parameters with validation metadata
    fragment_parameters = {
        'image_url': payload.image_url,
        'validated_at': datetime.utcnow().isoformat() + 'Z',
        'content_type': validation_result.content_type,
        'content_length': validation_result.content_length,
    }
    
    if payload.title:
        fragment_parameters['title'] = payload.title
    if payload.width:
        fragment_parameters['width'] = payload.width
    if payload.height:
        fragment_parameters['height'] = payload.height
    if payload.alt_text:
        fragment_parameters['alt_text'] = payload.alt_text
    else:
        fragment_parameters['alt_text'] = payload.title or 'Image'
    
    fragment_parameters['alignment'] = payload.alignment or 'center'
    fragment_parameters['require_https'] = payload.require_https
    
    # Add fragment to session
    output = await manager.add_fragment(
        session_id=payload.session_id,
        fragment_id='image_from_url',  # Standard fragment ID
        parameters=fragment_parameters,
        position=payload.position or 'end',
    )
    
    return _success(_model_dump(output))
```

## Usage Examples

### Basic Image
```json
{
  "tool": "add_image_fragment",
  "arguments": {
    "session_id": "abc-123-...",
    "image_url": "https://example.com/chart.png"
  }
}
```

### Image with Title and Sizing
```json
{
  "tool": "add_image_fragment",
  "arguments": {
    "session_id": "abc-123-...",
    "image_url": "https://example.com/chart.png",
    "title": "Q4 Sales Performance",
    "width": 800,
    "alt_text": "Bar chart showing quarterly sales growth",
    "alignment": "center"
  }
}
```

### HTTP URL (Relaxed Security)
```json
{
  "tool": "add_image_fragment",
  "arguments": {
    "session_id": "abc-123-...",
    "image_url": "http://internal-server.local/report.png",
    "require_https": false,
    "title": "Internal Report Chart"
  }
}
```

## Error Handling Examples

### Invalid URL
```
add_image_fragment(session_id="abc-123", image_url="not-a-url")

Response:
{
  "status": "error",
  "error_code": "INVALID_IMAGE_URL",
  "message": "Image URL must use HTTP or HTTPS protocol",
  "recovery": "Provide a valid HTTP or HTTPS URL",
  "details": {"reason": "Invalid URL scheme"}
}
```

### Non-Image URL
```
add_image_fragment(session_id="abc-123", image_url="https://example.com/doc.pdf")

Response:
{
  "status": "error",
  "error_code": "INVALID_IMAGE_CONTENT_TYPE",
  "message": "URL does not return a valid image content-type",
  "recovery": "Ensure the URL points to an image file. Allowed types: image/png, image/jpeg, image/gif, image/webp, image/svg+xml",
  "details": {
    "content_type": "application/pdf",
    "allowed_types": ["image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"]
  }
}
```

## Testing Requirements

1. **URL validation tests**
   - HTTPS requirement enforcement
   - HTTP support with require_https=false
   - Invalid schemes rejected
   - Malformed URLs rejected

2. **Accessibility tests**
   - 200 OK responses accepted
   - 404 Not Found rejected
   - 500 Server Error rejected
   - Timeout handling

3. **Content-Type tests**
   - Valid image types accepted (PNG, JPEG, GIF, WEBP, SVG)
   - Invalid types rejected (PDF, HTML, JSON, etc.)
   - Case-insensitive matching

4. **Size validation tests**
   - Images under limit accepted
   - Images over limit rejected
   - Missing Content-Length header handled

5. **Format-specific rendering tests**
   - PDF: Images embedded as base64
   - HTML: Images embedded as data URIs
   - Markdown: Images linked to URL

6. **Security tests**
   - Group isolation (can't add images to other groups' sessions)
   - HTTPS enforcement by default
   - HTTP only when explicitly allowed

## Configuration

### Environment Variables
```bash
# Image validation settings
DOCO_IMAGE_MAX_SIZE_MB=10          # Max image size in MB
DOCO_IMAGE_VALIDATION_TIMEOUT=10   # Validation timeout in seconds
DOCO_IMAGE_REQUIRE_HTTPS=true      # Enforce HTTPS by default
```

## Benefits

1. **Early error detection** - URL validated when added, not at render time
2. **Clear error messages** - Detailed errors with recovery guidance
3. **Format flexibility** - Embedded (PDF/HTML) or linked (Markdown)
4. **Security** - HTTPS enforcement with opt-out option
5. **Performance** - Markdown rendering doesn't download images
6. **Accessibility** - Alt text support for screen readers
7. **Scalability** - Configurable size limits and timeouts
