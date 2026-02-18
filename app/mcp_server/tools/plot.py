"""Plot tool handlers."""

from __future__ import annotations

from typing import Any, Dict

from mcp.types import ImageContent

from app.logger import Logger, session_logger
from app.mcp_server.responses import _error, _json_text, _model_dump, _success
from app.mcp_server.state import ensure_manager, get_components
from app.mcp_server.tool_types import ToolResponse
from app.mcp_server.tools.common import resolve_session_identifier
from app.plot import GraphParams
from app.validation.plot_models import (
    AddPlotFragmentInput,
    GetImageInput,
    ListImagesInput,
    RenderGraphInput,
)

logger: Logger = session_logger


async def _tool_render_graph(arguments: Dict[str, Any]) -> ToolResponse:
    """Render a graph visualization.

    Validates input, renders the graph, and returns either:
    - base64 image data (default mode)
    - storage GUID (proxy mode, for later retrieval via get_image)

    SECURITY: Requires valid JWT. Group isolation for proxy storage.
    """
    import base64 as b64_mod

    payload = RenderGraphInput.model_validate(arguments)
    caller_group = payload.group if hasattr(payload, "group") else "public"

    comps = get_components()
    renderer = None if comps is None else comps.plot_renderer
    if renderer is None:
        return _error(
            code="PLOT_NOT_INITIALIZED",
            message="Plot subsystem is not initialized",
            recovery="The server may not have started correctly. Try restarting.",
        )

    storage = None if comps is None else comps.plot_storage
    validator = None if comps is None else comps.plot_validator

    # Build GraphParams from validated input (exclude auth/group fields)
    param_fields = {
        k: v
        for k, v in payload.model_dump().items()
        if k not in ("auth_token", "token", "group") and v is not None
    }

    try:
        graph_data = GraphParams(**param_fields)
    except (ValueError, Exception) as e:
        return _error(
            code="INVALID_GRAPH_PARAMS",
            message=f"Invalid graph parameters: {str(e)}",
            recovery=(
                "Check required fields: 'title' is required, at least y1 (or y) "
                "must be provided as a list of numbers."
            ),
        )

    # Validate graph data
    if validator is not None:
        validation_result = validator.validate(graph_data)
        if not validation_result.is_valid:
            error_details = [err.to_dict() for err in validation_result.errors]
            return _error(
                code="GRAPH_VALIDATION_ERROR",
                message="Graph data validation failed",
                recovery="Review the validation errors and correct the input data.",
                details={"validation_errors": error_details},
            )

    # Proxy mode: render to bytes, save to storage, return GUID
    if graph_data.proxy:
        if storage is None:
            return _error(
                code="PLOT_STORAGE_NOT_INITIALIZED",
                message="Plot storage is not initialized",
                recovery="The server may not have started correctly. Try restarting.",
            )

        graph_data_bytes = graph_data.model_copy()
        object.__setattr__(graph_data_bytes, "return_base64", False)

        try:
            image_bytes = renderer.render(graph_data_bytes, group=caller_group)
            if isinstance(image_bytes, str):
                image_bytes = b64_mod.b64decode(image_bytes)
        except (ValueError, RuntimeError) as e:
            return _error(
                code="RENDER_ERROR",
                message=f"Graph rendering failed: {str(e)}",
                recovery=(
                    "Check your data arrays and chart type. Ensure arrays are non-empty "
                    "and of the same length."
                ),
            )

        guid = storage.save_image(
            image_data=image_bytes,
            format=graph_data.format,
            group=caller_group,
            alias=graph_data.alias,
        )

        result = {
            "guid": guid,
            "format": graph_data.format,
            "theme": graph_data.theme,
            "type": graph_data.type,
            "title": graph_data.title,
            "size_bytes": len(image_bytes),
        }
        if graph_data.alias:
            result["alias"] = graph_data.alias

        logger.info(
            "Plot rendered in proxy mode",
            guid=guid,
            format=graph_data.format,
            group=caller_group,
        )
        return _success(result, message=f"Graph saved with GUID: {guid}")

    # Non-proxy: render to base64 and return as ImageContent
    try:
        graph_data_b64 = graph_data.model_copy()
        object.__setattr__(graph_data_b64, "return_base64", True)
        encoded = renderer.render(graph_data_b64, group=caller_group)
        if isinstance(encoded, bytes):
            encoded = b64_mod.b64encode(encoded).decode("utf-8")
    except (ValueError, RuntimeError) as e:
        return _error(
            code="RENDER_ERROR",
            message=f"Graph rendering failed: {str(e)}",
            recovery=(
                "Check your data arrays and chart type. Ensure arrays are non-empty "
                "and of the same length."
            ),
        )

    mime_type = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "svg": "image/svg+xml",
        "pdf": "application/pdf",
    }.get(graph_data.format, "image/png")

    logger.info(
        "Plot rendered inline",
        format=graph_data.format,
        theme=graph_data.theme,
        chart_type=graph_data.type,
        group=caller_group,
    )

    return [
        ImageContent(type="image", data=encoded, mimeType=mime_type),
        _json_text(
            {
                "status": "success",
                "data": {
                    "format": graph_data.format,
                    "theme": graph_data.theme,
                    "type": graph_data.type,
                    "title": graph_data.title,
                },
            }
        ),
    ]


async def _tool_get_image(arguments: Dict[str, Any]) -> ToolResponse:
    """Retrieve a stored plot image by GUID or alias.

    SECURITY: Group isolation -- only images from the caller's group are accessible.
    """
    import base64 as b64_mod

    payload = GetImageInput.model_validate(arguments)
    caller_group = payload.group if hasattr(payload, "group") else "public"

    comps = get_components()
    storage = None if comps is None else comps.plot_storage
    if storage is None:
        return _error(
            code="PLOT_STORAGE_NOT_INITIALIZED",
            message="Plot storage is not initialized",
            recovery="The server may not have started correctly. Try restarting.",
        )

    result = storage.get_image(payload.identifier, group=caller_group)
    if result is None:
        return _error(
            code="IMAGE_NOT_FOUND",
            message=f"Image '{payload.identifier}' not found",
            recovery=(
                "Check the GUID or alias is correct. "
                "Call list_images to see available images in your group."
            ),
        )

    image_data, fmt = result
    encoded = b64_mod.b64encode(image_data).decode("utf-8")
    mime_type = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "svg": "image/svg+xml",
        "pdf": "application/pdf",
    }.get(fmt, "image/png")

    alias = storage.get_alias(
        storage.resolve_identifier(payload.identifier, caller_group) or payload.identifier
    )

    logger.info(
        "Plot image retrieved",
        identifier=payload.identifier,
        format=fmt,
        group=caller_group,
        size_bytes=len(image_data),
    )

    return [
        ImageContent(type="image", data=encoded, mimeType=mime_type),
        _json_text(
            {
                "status": "success",
                "data": {
                    "identifier": payload.identifier,
                    "format": fmt,
                    "size_bytes": len(image_data),
                    "alias": alias,
                },
            }
        ),
    ]


async def _tool_list_images(arguments: Dict[str, Any]) -> ToolResponse:
    """List all stored plot images accessible to the caller's group."""
    payload = ListImagesInput.model_validate(arguments)
    caller_group = payload.group if hasattr(payload, "group") else "public"

    comps = get_components()
    storage = None if comps is None else comps.plot_storage
    if storage is None:
        return _error(
            code="PLOT_STORAGE_NOT_INITIALIZED",
            message="Plot storage is not initialized",
            recovery="The server may not have started correctly. Try restarting.",
        )

    images = storage.list_images(group=caller_group)

    logger.info(
        "Plot images listed",
        group=caller_group,
        count=len(images),
    )

    return _success(
        {"images": images, "count": len(images)},
        message=f"Found {len(images)} plot image(s) in group '{caller_group}'",
    )


async def _tool_list_themes(arguments: Dict[str, Any]) -> ToolResponse:
    """List all available plot themes with descriptions."""
    from app.plot.themes import list_themes_with_descriptions

    themes = list_themes_with_descriptions()
    return _success(
        {"themes": themes, "count": len(themes)},
        message=f"Found {len(themes)} available theme(s)",
    )


async def _tool_list_handlers(arguments: Dict[str, Any]) -> ToolResponse:
    """List all available chart types (handlers) with descriptions."""
    from app.plot.handlers import list_handlers_with_descriptions

    handlers = list_handlers_with_descriptions()
    return _success(
        {"handlers": handlers, "count": len(handlers)},
        message=f"Found {len(handlers)} available chart type(s)",
    )


async def _tool_add_plot_fragment(arguments: Dict[str, Any]) -> ToolResponse:
    """Render a graph and embed it as a fragment in a document session.

    Two modes:
    1. GUID path: Provide 'plot_guid' to embed a previously rendered plot.
    2. Inline path: Provide render params (title, y1, etc.) to render and embed.

    Both paths produce a base64 data URI embedded as an image_from_url fragment.

    SECURITY: Validates session belongs to caller's group.
    """
    import base64 as b64_mod
    from datetime import datetime

    payload = AddPlotFragmentInput.model_validate(arguments)
    manager = ensure_manager()
    caller_group = payload.group if hasattr(payload, "group") else "public"

    # Resolve session alias to GUID if needed
    session_id = resolve_session_identifier(payload.session_id, caller_group, manager)
    if not session_id:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery=(
                "Verify the session_id or alias is correct. "
                "Call list_active_sessions to see your sessions."
            ),
        )

    # SECURITY: Verify session belongs to caller's group
    session = await manager.get_session(session_id)
    if session is None or session.group != caller_group:
        return _error(
            code="SESSION_NOT_FOUND",
            message=f"Session '{payload.session_id}' not found",
            recovery=(
                "Verify the session_id or alias is correct. "
                "Call list_active_sessions to see your sessions."
            ),
        )

    # Determine mode: GUID path vs inline render path
    if payload.plot_guid:
        # GUID path: fetch previously rendered plot from storage
        comps = get_components()
        storage = None if comps is None else comps.plot_storage
        if storage is None:
            return _error(
                code="PLOT_STORAGE_NOT_INITIALIZED",
                message="Plot storage is not initialized",
                recovery="The server may not have started correctly. Try restarting.",
            )

        data_uri = storage.get_image_as_data_uri(payload.plot_guid, group=caller_group)
        if data_uri is None:
            return _error(
                code="IMAGE_NOT_FOUND",
                message=f"Plot image '{payload.plot_guid}' not found",
                recovery=(
                    "Check the GUID is correct and belongs to your group. "
                    "Call list_images to see available images."
                ),
            )

        # Use title from payload as caption, or derive from GUID
        image_title = payload.title or f"Plot {payload.plot_guid[:8]}"
        content_type = "image/png"  # Default for stored images

        logger.info(
            "Embedding plot from GUID",
            plot_guid=payload.plot_guid,
            session_id=session_id,
            group=caller_group,
        )

    else:
        # Inline render path: render the graph in-process
        if payload.title is None:
            return _error(
                code="MISSING_TITLE",
                message="'title' is required for inline render mode",
                recovery=(
                    "Provide a 'title' parameter, or use 'plot_guid' "
                    "to embed a previously rendered plot."
                ),
            )

        comps = get_components()
        renderer = None if comps is None else comps.plot_renderer
        if renderer is None:
            return _error(
                code="PLOT_NOT_INITIALIZED",
                message="Plot subsystem is not initialized",
                recovery="The server may not have started correctly. Try restarting.",
            )

        # Build GraphParams from inline render fields
        render_fields = {}
        for field_name in (
            "title",
            "x",
            "y",
            "y1",
            "y2",
            "y3",
            "y4",
            "y5",
            "label1",
            "label2",
            "label3",
            "label4",
            "label5",
            "color1",
            "color2",
            "color3",
            "color4",
            "color5",
            "color",
            "xlabel",
            "ylabel",
            "type",
            "format",
            "theme",
            "line_width",
            "marker_size",
            "alpha",
        ):
            val = getattr(payload, field_name, None)
            if val is not None:
                render_fields[field_name] = val

        try:
            graph_data = GraphParams(**render_fields)
        except (ValueError, Exception) as e:
            return _error(
                code="INVALID_GRAPH_PARAMS",
                message=f"Invalid graph parameters: {str(e)}",
                recovery="Check required fields: 'title' and at least y1 (or y) must be provided.",
            )

        # Validate
        validator = None if comps is None else comps.plot_validator
        if validator is not None:
            validation_result = validator.validate(graph_data)
            if not validation_result.is_valid:
                error_details = [err.to_dict() for err in validation_result.errors]
                return _error(
                    code="GRAPH_VALIDATION_ERROR",
                    message="Graph data validation failed",
                    recovery="Review the validation errors and correct the input data.",
                    details={"validation_errors": error_details},
                )

        # Render to bytes
        try:
            image_bytes = renderer.render_to_bytes(graph_data)
        except (ValueError, RuntimeError) as e:
            return _error(
                code="RENDER_ERROR",
                message=f"Graph rendering failed: {str(e)}",
                recovery="Check your data arrays and chart type.",
            )

        content_type = f"image/{graph_data.format}"
        if graph_data.format == "jpg":
            content_type = "image/jpeg"
        elif graph_data.format == "svg":
            content_type = "image/svg+xml"

        encoded = b64_mod.b64encode(image_bytes).decode("utf-8")
        data_uri = f"data:{content_type};base64,{encoded}"
        image_title = payload.title

        logger.info(
            "Embedding inline-rendered plot",
            chart_type=graph_data.type,
            session_id=session_id,
            group=caller_group,
        )

    # Build fragment parameters (same pattern as add_image_fragment)
    fragment_parameters: Dict[str, Any] = {
        "image_url": "inline:plot",  # Marker for inline content
        "embedded_data_uri": data_uri,
        "validated_at": datetime.utcnow().isoformat() + "Z",
        "content_type": content_type,
    }

    if image_title:
        fragment_parameters["title"] = image_title
    if payload.width:
        fragment_parameters["width"] = payload.width
    if payload.height:
        fragment_parameters["height"] = payload.height

    fragment_parameters["alt_text"] = payload.alt_text or image_title or "Plot"
    fragment_parameters["alignment"] = payload.alignment or "center"

    # Add fragment to session using standard image fragment
    output = await manager.add_fragment(
        session_id=session_id,
        fragment_id="image_from_url",
        parameters=fragment_parameters,
        position=payload.position or "end",
    )

    logger.info(
        "Plot fragment added to session",
        session_id=session_id,
        group=caller_group,
        mode="guid" if payload.plot_guid else "inline",
    )

    return _success(_model_dump(output))
