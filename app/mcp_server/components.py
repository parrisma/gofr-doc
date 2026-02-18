"""Component initialization for the MCP server.

This module centralizes initialization of registries/managers/engines used by
tool handlers.

Behavior must remain identical to the legacy initialization previously defined
in app/mcp_server/mcp_server.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.config import get_default_sessions_dir
from app.logger import Logger
from app.plot import GraphDataValidator, GraphRenderer
from app.plot.storage import PlotStorageWrapper
from app.rendering import RenderingEngine
from app.sessions import SessionManager, SessionStore
from app.storage.common_adapter import CommonStorageAdapter
from app.styles import StyleRegistry
from app.templates import TemplateRegistry


@dataclass
class ServerComponents:
    template_registry: TemplateRegistry
    style_registry: StyleRegistry
    session_store: SessionStore
    session_manager: SessionManager
    rendering_engine: RenderingEngine
    plot_renderer: GraphRenderer
    plot_storage: Optional[PlotStorageWrapper]
    plot_validator: GraphDataValidator


def initialize_components(
    *,
    templates_dir_override: Optional[str],
    styles_dir_override: Optional[str],
    logger: Logger,
) -> ServerComponents:
    """Initialize all server components.

    Args:
            templates_dir_override: Optional templates directory override (tests)
            styles_dir_override: Optional styles directory override (tests)
            logger: Logger
    """
    project_root = Path(__file__).parent.parent.parent

    templates_dir = templates_dir_override or str(project_root / "data" / "templates")
    styles_dir = styles_dir_override or str(project_root / "data" / "styles")

    template_registry = TemplateRegistry(templates_dir=templates_dir, logger=logger)
    style_registry = StyleRegistry(styles_dir=styles_dir, logger=logger)
    session_store = SessionStore(base_dir=get_default_sessions_dir(), logger=logger)
    session_manager = SessionManager(
        session_store=session_store,
        template_registry=template_registry,
        logger=logger,
    )
    rendering_engine = RenderingEngine(
        template_registry=template_registry,
        style_registry=style_registry,
        logger=logger,
    )

    # Initialize plot domain components
    from app.storage import get_storage

    plot_renderer = GraphRenderer(logger=logger)
    plot_validator = GraphDataValidator()
    storage_adapter_raw = get_storage()
    if not isinstance(storage_adapter_raw, CommonStorageAdapter):
        logger.warning(
            "Plot storage requires CommonStorageAdapter but got legacy storage. "
            "Plot proxy mode will not work.",
        )
        plot_storage = None
    else:
        plot_storage = PlotStorageWrapper(storage=storage_adapter_raw, logger=logger)
    logger.info("Plot domain components initialized")

    return ServerComponents(
        template_registry=template_registry,
        style_registry=style_registry,
        session_store=session_store,
        session_manager=session_manager,
        rendering_engine=rendering_engine,
        plot_renderer=plot_renderer,
        plot_storage=plot_storage,
        plot_validator=plot_validator,
    )
