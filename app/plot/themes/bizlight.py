"""Professional business light theme."""

from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

from app.plot.themes.base import Theme


class BizLightTheme(Theme):
    """Professional business light theme with clean, corporate styling."""

    def __init__(self):
        self.background_color = "#FFFFFF"
        self.text_color = "#222222"
        self.grid_color = "#D0D4D9"
        self.default_color = "#2F6DB2"
        self.colors = [
            "#2F6DB2",  # blue
            "#C97A1E",  # orange
            "#4BAA7B",  # green
            "#D35C56",  # red
            "#7E6BB3",  # purple
            "#B98A68",  # brown
            "#D78A9C",  # pink
            "#5F6B7A",  # gray
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
            "name": "bizlight",
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
            "Professional business light theme with corporate styling and refined "
            "color palette, suitable for executive dashboards and client presentations"
        )
