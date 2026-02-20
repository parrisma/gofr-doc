"""Base class for graph type handlers."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from app.plot.graph_params import GraphParams


class GraphHandler(ABC):
    """Base class for graph type handlers."""

    @abstractmethod
    def plot(self, ax: "Axes", data: "GraphParams") -> None:
        """Plot the graph on the given axes."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get a human-readable description of the handler."""
        pass
