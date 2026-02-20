from __future__ import annotations

from typing import Optional

# Optional directory overrides (set by main_mcp.py for testing)
templates_dir_override: Optional[str] = None
styles_dir_override: Optional[str] = None

# Web server URL for proxy mode (set by main_mcp.py)
web_url_override: Optional[str] = None
proxy_url_mode: str = "url"  # "guid" or "url" - controls proxy response format
