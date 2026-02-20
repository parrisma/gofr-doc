"""Abstract base class for graph themes."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


class Theme(ABC):
    """Abstract base class for graph themes."""

    @abstractmethod
    def apply(self, fig: "Figure", ax: "Axes") -> None:
        """Apply the theme to a figure and axes."""
        pass

    @abstractmethod
    def get_default_color(self) -> str:
        """Get the default color for plots."""
        pass

    @abstractmethod
    def get_colors(self) -> list[str]:
        """Get a list of theme colors for multi-series plots."""
        pass

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get theme configuration as a dictionary."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get a human-readable description of the theme."""
        pass
