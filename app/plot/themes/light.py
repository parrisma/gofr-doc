"""Light theme with clean, bright colors."""

from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

from app.plot.themes.base import Theme


class LightTheme(Theme):
    """Light theme with clean, bright colors."""

    def __init__(self):
        self.background_color = "#FFFFFF"
        self.text_color = "#000000"
        self.grid_color = "#E0E0E0"
        self.default_color = "#1f77b4"
        self.colors = [
            "#1f77b4",  # blue
            "#ff7f0e",  # orange
            "#2ca02c",  # green
            "#d62728",  # red
            "#9467bd",  # purple
            "#8c564b",  # brown
            "#e377c2",  # pink
            "#7f7f7f",  # gray
        ]
        self.font_family = "sans-serif"
        self.font_size = 10

    def apply(self, fig: "Figure", ax: "Axes") -> None:
        fig.patch.set_facecolor(self.background_color)
        ax.set_facecolor(self.background_color)
        ax.title.set_color(self.text_color)
        ax.xaxis.label.set_color(self.text_color)
        ax.yaxis.label.set_color(self.text_color)
        ax.tick_params(colors=self.text_color)
        for spine in ax.spines.values():
            spine.set_edgecolor(self.grid_color)
        ax.grid(True, alpha=0.3, color=self.grid_color)
        ax.title.set_fontfamily(self.font_family)
        ax.xaxis.label.set_fontfamily(self.font_family)
        ax.yaxis.label.set_fontfamily(self.font_family)
        ax.title.set_fontsize(self.font_size + 2)
        ax.xaxis.label.set_fontsize(self.font_size)
        ax.yaxis.label.set_fontsize(self.font_size)

    def get_default_color(self) -> str:
        return self.default_color

    def get_colors(self) -> list[str]:
        return self.colors

    def get_config(self) -> Dict[str, Any]:
        return {
            "name": "light",
            "background_color": self.background_color,
            "text_color": self.text_color,
            "grid_color": self.grid_color,
            "default_color": self.default_color,
            "colors": self.colors,
            "font_family": self.font_family,
            "font_size": self.font_size,
        }

    def get_description(self) -> str:
        return (
            "Clean and bright theme with high contrast colors, ideal for "
            "presentations and reports in well-lit environments"
        )
