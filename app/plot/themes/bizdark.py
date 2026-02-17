"""Professional business dark theme."""

from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

from app.plot.themes.base import Theme


class BizDarkTheme(Theme):
    """Professional business dark theme with low-glare, high-legibility styling."""

    def __init__(self):
        self.background_color = "#0F1113"
        self.text_color = "#E6E6E6"
        self.grid_color = "#3A3F44"
        self.default_color = "#2F6DB2"
        self.colors = [
            "#2F6DB2",  # blue
            "#C97A1E",  # muted orange
            "#4BAA7B",  # muted green
            "#D35C56",  # muted red
            "#7E6BB3",  # muted purple
            "#B98A68",  # muted brown
            "#D78A9C",  # muted pink
            "#99A3AD",  # neutral gray
        ]
        self.font_family = "DejaVu Sans"
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
        return list(self.colors)

    def get_config(self) -> Dict[str, Any]:
        return {
            "name": "bizdark",
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
            "Professional business dark theme with low-glare background and "
            "high-legibility text, optimized for trading terminals and extended analysis sessions"
        )
