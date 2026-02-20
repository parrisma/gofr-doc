"""Line graph handler."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from app.plot.graph_params import GraphParams

from app.plot.handlers.base import GraphHandler


class LineGraphHandler(GraphHandler):
    """Handler for line graphs with support for multiple datasets."""

    def plot(self, ax: "Axes", data: "GraphParams") -> None:
        """Plot line graph supporting multiple datasets (y1-y5).

        Raises:
            ValueError: If data cannot be plotted
        """
        try:
            datasets = data.get_datasets()
            if not datasets:
                raise ValueError("No datasets provided (y1 is required)")

            x_values = data.get_x_values(len(datasets[0][0]))

            for i, (y_data, label, color) in enumerate(datasets):
                kwargs: dict[str, Any] = {"linewidth": data.line_width, "alpha": data.alpha}
                if color:
                    kwargs["color"] = color
                if label:
                    kwargs["label"] = label
                ax.plot(x_values, y_data, **kwargs)

            if any(label for _, label, _ in datasets):
                ax.legend()
        except Exception as e:
            raise ValueError(f"Failed to plot line graph: {str(e)}")

    def get_description(self) -> str:
        return (
            "Line chart for visualizing trends and continuous data over time "
            "or ordered categories, supports multiple datasets with connecting lines"
        )
