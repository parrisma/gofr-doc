"""Test server launcher and management

Handles starting MCP and web servers in secure (auth) mode for testing.
Ensures servers use the same JWT secret and token store as test fixtures.
"""

import subprocess
import os
import time
import httpx
from typing import Optional
from app.logger import Logger, session_logger


class ServerManager:
    """Manages test server lifecycle (MCP and web servers in auth mode)"""

    def __init__(
        self,
        jwt_secret: str,
        token_store_path: str,
        mcp_port: int = 8013,
        web_port: int = 8000,
    ):
        """
        Initialize test server manager

        Args:
            jwt_secret: JWT secret to use for token signing
            token_store_path: Path to token store file
            mcp_port: Port for MCP server (default: 8013 for testing)
            web_port: Port for web server (default: 8000 for testing)
        """
        self.jwt_secret = jwt_secret
        self.token_store_path = token_store_path
        self.mcp_port = mcp_port
        self.web_port = web_port
        self.logger: Logger = session_logger

        self.mcp_process: Optional[subprocess.Popen] = None
        self.web_process: Optional[subprocess.Popen] = None

    def start_mcp_server(
        self,
        templates_dir: str,
        styles_dir: str,
        storage_dir: Optional[str] = None,
    ) -> bool:
        """
        Start MCP server in auth mode

        Args:
            templates_dir: Path to templates directory
            styles_dir: Path to styles directory
            storage_dir: Path to storage directory (optional)

        Returns:
            True if server started successfully
        """
        try:
            # Prepare environment with auth settings
            env = os.environ.copy()
            env["DOCO_JWT_SECRET"] = self.jwt_secret
            env["DOCO_TOKEN_STORE"] = self.token_store_path

            # Build command
            cmd = [
                "python",
                "app/main_mcp.py",
                "--templates-dir",
                templates_dir,
                "--styles-dir",
                styles_dir,
                f"--port={self.mcp_port}",
            ]

            # Only add storage-dir if provided
            if storage_dir:
                cmd.extend(["--storage-dir", storage_dir])

            self.logger.info(
                "Starting MCP server in auth mode",
                port=self.mcp_port,
                cmd=" ".join(cmd),
            )

            # Start server
            self.mcp_process = subprocess.Popen(
                cmd,
                cwd="/home/gofr-doc/devroot/gofr-doc",
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for server to be ready
            return self._wait_for_server(f"http://localhost:{self.mcp_port}/mcp/", timeout=10)

        except Exception as e:
            self.logger.error("Failed to start MCP server", error=str(e))
            return False

    def start_web_server(
        self,
        templates_dir: str,
        styles_dir: str,
        storage_dir: Optional[str] = None,
    ) -> bool:
        """
        Start web server in auth mode

        Args:
            templates_dir: Path to templates directory
            styles_dir: Path to styles directory
            storage_dir: Path to storage directory (optional)

        Returns:
            True if server started successfully
        """
        try:
            # Prepare environment with auth settings
            env = os.environ.copy()
            env["DOCO_JWT_SECRET"] = self.jwt_secret
            env["DOCO_TOKEN_STORE"] = self.token_store_path

            # Build command
            cmd = [
                "python",
                "app/main_web.py",
                "--templates-dir",
                templates_dir,
                "--styles-dir",
                styles_dir,
                f"--port={self.web_port}",
            ]

            # Only add storage-dir if provided
            if storage_dir:
                cmd.extend(["--storage-dir", storage_dir])

            self.logger.info(
                "Starting web server in auth mode",
                port=self.web_port,
                cmd=" ".join(cmd),
            )

            # Start server
            self.web_process = subprocess.Popen(
                cmd,
                cwd="/home/gofr-doc/devroot/gofr-doc",
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for server to be ready
            return self._wait_for_server(f"http://localhost:{self.web_port}/ping", timeout=10)

        except Exception as e:
            self.logger.error("Failed to start web server", error=str(e))
            return False

    def _wait_for_server(self, url: str, timeout: int = 10) -> bool:
        """
        Wait for server to become ready by checking health endpoint

        Args:
            url: Health check URL
            timeout: Maximum seconds to wait

        Returns:
            True if server is ready, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = httpx.get(url, timeout=2)
                if response.status_code < 500:
                    self.logger.info("Server is ready", url=url)
                    return True
            except (httpx.RequestError, httpx.TimeoutException):
                pass

            time.sleep(0.5)

        self.logger.error("Server did not become ready within timeout", url=url, timeout=timeout)
        return False

    def stop_mcp_server(self) -> None:
        """Stop MCP server gracefully"""
        if self.mcp_process:
            try:
                self.logger.info("Stopping MCP server", pid=self.mcp_process.pid)
                self.mcp_process.terminate()
                try:
                    self.mcp_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.warning("MCP server did not stop gracefully, killing")
                    self.mcp_process.kill()
                    self.mcp_process.wait()
            except Exception as e:
                self.logger.error("Error stopping MCP server", error=str(e))
            finally:
                self.mcp_process = None

    def stop_web_server(self) -> None:
        """Stop web server gracefully"""
        if self.web_process:
            try:
                self.logger.info("Stopping web server", pid=self.web_process.pid)
                self.web_process.terminate()
                try:
                    self.web_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.warning("Web server did not stop gracefully, killing")
                    self.web_process.kill()
                    self.web_process.wait()
            except Exception as e:
                self.logger.error("Error stopping web server", error=str(e))
            finally:
                self.web_process = None

    def stop_all(self) -> None:
        """Stop all servers"""
        self.stop_mcp_server()
        self.stop_web_server()

    def get_mcp_url(self) -> str:
        """Get MCP server URL"""
        return f"http://localhost:{self.mcp_port}/mcp/"

    def get_web_url(self) -> str:
        """Get web server URL"""
        return f"http://localhost:{self.web_port}"
