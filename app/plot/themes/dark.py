"""Dark theme with muted colors for reduced eye strain."""

from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

from app.plot.themes.base import Theme


class DarkTheme(Theme):
    """Dark theme with muted colors for reduced eye strain."""

    def __init__(self):
        self.background_color = "#1E1E1E"
        self.text_color = "#E0E0E0"
        self.grid_color = "#3A3A3A"
        self.default_color = "#5DADE2"
        self.colors = [
            "#5DADE2",  # light blue
            "#F39C12",  # orange
            "#58D68D",  # green
            "#EC7063",  # red
            "#BB8FCE",  # purple
            "#E59866",  # brown
            "#F1948A",  # pink
            "#AEB6BF",  # gray
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
        ax.grid(True, alpha=0.2, color=self.grid_color)
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
            "name": "dark",
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
            "Dark theme with muted colors designed to reduce eye strain, "
            "perfect for extended viewing sessions and low-light environments"
        )
