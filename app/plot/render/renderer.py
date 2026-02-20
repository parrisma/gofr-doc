"""Graph renderer implementation.

Main renderer class that coordinates the rendering pipeline.
Uses the Agg backend for headless rendering in containers.
"""

import matplotlib

matplotlib.use("Agg")  # Must be set before importing pyplot

import matplotlib.pyplot as plt  # noqa: E402
import io  # noqa: E402
import base64  # noqa: E402
from typing import Optional  # noqa: E402

from app.plot.graph_params import GraphParams  # noqa: E402
from app.plot.handlers import get_handler  # noqa: E402
from app.plot.themes import get_theme  # noqa: E402
from app.logger import Logger, session_logger  # noqa: E402


class GraphRenderer:
    """Main renderer that delegates to specific graph handlers via registry."""

    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger or session_logger

    def render(self, data: GraphParams, group: Optional[str] = None) -> str | bytes:
        """Render a graph based on the provided data.

        Args:
            data: GraphParams containing all parameters for rendering
            group: Optional group name for storage access control

        Returns:
            Base64-encoded string or raw image bytes (proxy mode handled externally)

        Raises:
            ValueError: If graph type is not supported or theme is invalid
            RuntimeError: If rendering fails
        """
        fig = None
        buf = None

        datasets = data.get_datasets()
        data_points = len(datasets[0][0]) if datasets else 0

        self.logger.info(
            "Starting render",
            chart_type=data.type,
            format=data.format,
            theme=data.theme,
            num_datasets=len(datasets),
            data_points=data_points,
        )

        try:
            handler = get_handler(data.type)
            theme = get_theme(data.theme)

            fig, ax = plt.subplots()
            theme.apply(fig, ax)

            # Use theme default color if no color specified
            if data.color is None:
                data.color = theme.get_default_color()

            handler.plot(ax, data)

            ax.set_title(data.title)
            ax.set_xlabel(data.xlabel)
            ax.set_ylabel(data.ylabel)

            # Apply axis limits
            if data.xmin is not None or data.xmax is not None:
                ax.set_xlim(left=data.xmin, right=data.xmax)
            if data.ymin is not None or data.ymax is not None:
                ax.set_ylim(bottom=data.ymin, top=data.ymax)

            # Apply ticks
            if data.x_major_ticks is not None:
                ax.set_xticks(data.x_major_ticks)
            if data.y_major_ticks is not None:
                ax.set_yticks(data.y_major_ticks)
            if data.x_minor_ticks is not None:
                ax.set_xticks(data.x_minor_ticks, minor=True)
            if data.y_minor_ticks is not None:
                ax.set_yticks(data.y_minor_ticks, minor=True)

            # Save to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format=data.format, facecolor=fig.get_facecolor())
            buf.seek(0)
            image_data = buf.read()

            if data.return_base64:
                encoded = base64.b64encode(image_data).decode("utf-8")
                self.logger.info(
                    "Render completed",
                    chart_type=data.type,
                    format=data.format,
                    output_size_bytes=len(image_data),
                )
                return encoded

            self.logger.info(
                "Render completed (raw bytes)",
                chart_type=data.type,
                format=data.format,
                output_size_bytes=len(image_data),
            )
            return image_data

        except (ValueError, RuntimeError):
            raise
        except Exception as e:
            self.logger.error(
                "Unexpected error during rendering",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise RuntimeError(f"Unexpected error during rendering: {str(e)}")
        finally:
            if fig is not None:
                plt.close(fig)
            if buf is not None:
                buf.close()

    def render_to_bytes(self, data: GraphParams) -> bytes:
        """Render a graph and always return raw bytes (for embedding).

        Temporarily overrides return_base64 to False to get raw bytes.
        """
        # Make a copy to avoid mutating the input
        params = data.model_copy()
        object.__setattr__(params, "return_base64", False)
        result = self.render(params)
        if isinstance(result, str):
            # Should not happen with return_base64=False, but safety
            return base64.b64decode(result)
        return result
