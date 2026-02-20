from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Union

from mcp.types import EmbeddedResource, ImageContent, TextContent

ToolResponse = List[Union[TextContent, ImageContent, EmbeddedResource]]
ToolHandler = Callable[[Dict[str, Any]], Awaitable[ToolResponse]]
