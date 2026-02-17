"""Graph rendering parameters.

Defines the data model for graph rendering requests.
"""

from pydantic import BaseModel
from typing import List, Optional


class GraphParams(BaseModel):
    """Parameters for rendering a graph with support for up to 5 datasets."""

    title: str

    # X-axis data (optional, defaults to indices if not provided)
    x: Optional[List[float]] = None

    # Y-axis datasets (at least y1 or y is required, up to y5 supported)
    y1: Optional[List[float]] = None
    y2: Optional[List[float]] = None
    y3: Optional[List[float]] = None
    y4: Optional[List[float]] = None
    y5: Optional[List[float]] = None

    # Labels for each dataset (optional)
    label1: Optional[str] = None
    label2: Optional[str] = None
    label3: Optional[str] = None
    label4: Optional[str] = None
    label5: Optional[str] = None

    # Colors for each dataset (optional, uses theme defaults if not provided)
    color1: Optional[str] = None
    color2: Optional[str] = None
    color3: Optional[str] = None
    color4: Optional[str] = None
    color5: Optional[str] = None

    xlabel: str = "X-axis"
    ylabel: str = "Y-axis"
    type: str = "line"
    format: str = "png"
    return_base64: bool = True
    proxy: bool = False
    alias: Optional[str] = None
    line_width: float = 2.0
    marker_size: float = 36.0
    alpha: float = 1.0
    theme: str = "light"

    # Backward compatibility: accept old 'y' parameter and map to y1
    y: Optional[List[float]] = None
    color: Optional[str] = None

    # Axis limits
    xmin: Optional[float] = None
    xmax: Optional[float] = None
    ymin: Optional[float] = None
    ymax: Optional[float] = None

    # Major tick settings
    x_major_ticks: Optional[List[float]] = None
    y_major_ticks: Optional[List[float]] = None

    # Minor tick settings
    x_minor_ticks: Optional[List[float]] = None
    y_minor_ticks: Optional[List[float]] = None

    def model_post_init(self, __context) -> None:
        """Handle backward compatibility for old x,y,color parameters."""
        # Map old 'y' to 'y1' if y1 not provided
        if self.y is not None and self.y1 is None:
            object.__setattr__(self, "y1", self.y)

        # Validate that at least y1 or y is provided
        if self.y1 is None and self.y is None:
            raise ValueError(
                "At least one dataset (y1 or y for backward compatibility) is required"
            )

        # Map old 'color' to 'color1' if color1 not provided
        if self.color is not None and self.color1 is None:
            object.__setattr__(self, "color1", self.color)

    def get_datasets(self) -> List[tuple[List[float], Optional[str], Optional[str]]]:
        """Get all datasets as list of (y_data, label, color) tuples."""
        datasets = []
        for i in range(1, 6):
            y_data = getattr(self, f"y{i}", None)
            if y_data is not None:
                label = getattr(self, f"label{i}", None)
                color = getattr(self, f"color{i}", None)
                datasets.append((y_data, label, color))
        return datasets

    def get_x_values(self, y_length: int) -> List[float]:
        """Get x-axis values, generating indices if not provided."""
        if self.x is not None:
            return self.x
        return list(range(y_length))
