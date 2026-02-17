"""Pydantic input models for plot MCP tools.

Analogous to app/validation/models/inputs.py for document tools.
These models are used by handle_call_tool's Pydantic validation error handler
to provide structured error messages when input validation fails.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class RenderGraphInput(BaseModel):
    """Input for render_graph tool.

    Args:
        title: Graph title (required)
        y1: First dataset (required unless 'y' provided for backward compat)
        x: X-axis data points (optional, auto-generated indices if omitted)
        y2-y5: Additional datasets (optional)
        label1-label5: Dataset labels (optional)
        color1-color5: Dataset colors (optional)
        xlabel/ylabel: Axis labels
        type: Chart type (line, scatter, bar)
        format: Output format (png, jpg, svg, pdf)
        proxy: If True, save to storage and return GUID
        alias: Friendly name for proxy mode
        theme: Visual theme
        auth_token: JWT authentication token (primary)
        token: JWT authentication token (legacy backward compat)
        group: Group context (injected from JWT)
    """

    model_config = ConfigDict(extra="ignore")

    title: str
    x: Optional[List[float]] = None
    y: Optional[List[float]] = None
    y1: Optional[List[float]] = None
    y2: Optional[List[float]] = None
    y3: Optional[List[float]] = None
    y4: Optional[List[float]] = None
    y5: Optional[List[float]] = None
    label1: Optional[str] = None
    label2: Optional[str] = None
    label3: Optional[str] = None
    label4: Optional[str] = None
    label5: Optional[str] = None
    color1: Optional[str] = None
    color2: Optional[str] = None
    color3: Optional[str] = None
    color4: Optional[str] = None
    color5: Optional[str] = None
    color: Optional[str] = None
    xlabel: str = "X-axis"
    ylabel: str = "Y-axis"
    type: str = "line"
    format: str = "png"
    proxy: bool = False
    alias: Optional[str] = None
    line_width: float = 2.0
    marker_size: float = 36.0
    alpha: float = 1.0
    theme: str = "light"
    xmin: Optional[float] = None
    xmax: Optional[float] = None
    ymin: Optional[float] = None
    ymax: Optional[float] = None
    x_major_ticks: Optional[List[float]] = None
    y_major_ticks: Optional[List[float]] = None
    x_minor_ticks: Optional[List[float]] = None
    y_minor_ticks: Optional[List[float]] = None
    auth_token: Optional[str] = None
    token: Optional[str] = None
    group: str = "public"


class GetImageInput(BaseModel):
    """Input for get_image tool.

    Args:
        identifier: GUID or alias of the stored image
        auth_token: JWT authentication token (primary)
        token: JWT authentication token (legacy backward compat)
        group: Group context (injected from JWT)
    """

    model_config = ConfigDict(extra="ignore")

    identifier: str
    auth_token: Optional[str] = None
    token: Optional[str] = None
    group: str = "public"


class ListImagesInput(BaseModel):
    """Input for list_images tool.

    Args:
        auth_token: JWT authentication token (primary)
        token: JWT authentication token (legacy backward compat)
        group: Group context (injected from JWT)
    """

    model_config = ConfigDict(extra="ignore")

    auth_token: Optional[str] = None
    token: Optional[str] = None
    group: str = "public"


class AddPlotFragmentInput(BaseModel):
    """Input for add_plot_fragment tool.

    Supports two paths:
    1. GUID path: provide plot_guid to embed a previously rendered plot
    2. Inline path: provide render params (title, y1, etc.) to render and embed in one call

    Args:
        session_id: Document session GUID or alias (required)
        plot_guid: GUID of a previously rendered plot (optional, mutually exclusive with inline params)
        title: Graph title (required for inline path, optional caption for GUID path)
        x, y1..y5, label1..label5, color1..color5: Inline render params
        xlabel, ylabel, type, format, theme: Render settings for inline path
        width: Image width in pixels (optional)
        height: Image height in pixels (optional)
        alt_text: Accessibility text (optional)
        alignment: Image alignment: left, center, right (default: center)
        position: Fragment position (end, start, before:<guid>, after:<guid>)
        auth_token: JWT authentication token (primary)
        token: JWT authentication token (legacy backward compat)
        group: Group context (injected from JWT)
    """

    model_config = ConfigDict(extra="ignore")

    session_id: str
    plot_guid: Optional[str] = None

    # Inline render params (used when plot_guid is not provided)
    title: Optional[str] = None
    x: Optional[List[float]] = None
    y: Optional[List[float]] = None
    y1: Optional[List[float]] = None
    y2: Optional[List[float]] = None
    y3: Optional[List[float]] = None
    y4: Optional[List[float]] = None
    y5: Optional[List[float]] = None
    label1: Optional[str] = None
    label2: Optional[str] = None
    label3: Optional[str] = None
    label4: Optional[str] = None
    label5: Optional[str] = None
    color1: Optional[str] = None
    color2: Optional[str] = None
    color3: Optional[str] = None
    color4: Optional[str] = None
    color5: Optional[str] = None
    color: Optional[str] = None
    xlabel: str = "X-axis"
    ylabel: str = "Y-axis"
    type: str = "line"
    format: str = "png"
    theme: str = "light"
    line_width: float = 2.0
    marker_size: float = 36.0
    alpha: float = 1.0

    # Image fragment params
    width: Optional[int] = None
    height: Optional[int] = None
    alt_text: Optional[str] = None
    alignment: str = "center"
    position: Optional[str] = None

    auth_token: Optional[str] = None
    token: Optional[str] = None
    group: str = "public"
