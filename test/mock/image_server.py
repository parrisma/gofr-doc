"""Lightweight HTTP server for serving test images.

Provides a simple HTTP server that serves images from test/mock/data directory
for testing image fragment downloads without external network dependencies.
"""

import http.server
import socketserver
from pathlib import Path
from threading import Thread


class ImageServerHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler that serves files from test/mock/data directory."""

    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from
        self.directory = str(Path(__file__).parent / "data")
        super().__init__(*args, directory=self.directory, **kwargs)

    def log_message(self, format, *args):
        """Suppress server logs during testing."""
        pass

    def end_headers(self):
        """Add CORS headers to allow cross-origin requests."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.end_headers()


class ImageServer:
    """Lightweight HTTP server for testing image downloads."""

    def __init__(self, port: int = 8765):
        """Initialize the image server.

        Args:
            port: Port number to bind the server to (default: 8765)
        """
        self.port = port
        self.httpd = None
        self.thread = None

    def start(self):
        """Start the server in a background thread."""
        if self.httpd is not None:
            return  # Already running

        # Create server with reusable address
        socketserver.TCPServer.allow_reuse_address = True
        self.httpd = socketserver.TCPServer(("", self.port), ImageServerHandler)

        # Start server in background thread
        self.thread = Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the server."""
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
            self.thread = None

    def get_url(self, filename: str) -> str:
        """Get the full URL for a file served by this server.

        In Docker mode the MCP container needs to reach this server via the
        dev container's hostname on the shared test network.  Falls back to
        ``localhost`` when not running inside Docker.

        Args:
            filename: Name of the file in test/mock/data directory

        Returns:
            Full HTTP URL to access the file
        """
        import os

        host = os.environ.get("GOFR_DOC_IMAGE_SERVER_HOST", "localhost")
        return f"http://{host}:{self.port}/{filename}"

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
