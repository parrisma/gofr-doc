from __future__ import annotations

from typing import Optional

from app.rendering import RenderingEngine
from app.sessions import SessionManager
from app.styles import StyleRegistry
from app.templates import TemplateRegistry

from app.mcp_server.components import ServerComponents

components: Optional[ServerComponents] = None


def set_components(value: ServerComponents) -> None:
    global components
    components = value


def require_components() -> None:
    if components is None:
        raise RuntimeError("Server components have not been initialised")


def get_components() -> Optional[ServerComponents]:
    return components


def ensure_template_registry() -> TemplateRegistry:
    require_components()
    assert components is not None
    return components.template_registry


def ensure_style_registry() -> StyleRegistry:
    require_components()
    assert components is not None
    return components.style_registry


def ensure_manager() -> SessionManager:
    require_components()
    assert components is not None
    return components.session_manager


def ensure_renderer() -> RenderingEngine:
    require_components()
    assert components is not None
    return components.rendering_engine
