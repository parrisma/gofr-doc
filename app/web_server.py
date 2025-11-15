from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse, Response, HTMLResponse
from app.validation import GraphDataValidator
from app.storage import get_storage
from app.auth import TokenInfo, verify_token, optional_verify_token, init_auth_service
from app.logger import Logger, session_logger
from datetime import datetime
import base64
import os
from typing import Optional


class DocoWebServer:
    def __init__(
        self,
        jwt_secret: Optional[str] = None,
        token_store_path: Optional[str] = None,
        require_auth: bool = True,
    ):
        self.app = FastAPI(title="doco", description="Document rendering service")
        self.renderer = GraphRenderer()
        self.validator = GraphDataValidator()
        self.storage = get_storage()
        self.require_auth = require_auth

        # Initialize auth service only if auth is required
        if require_auth:
            init_auth_service(secret_key=jwt_secret, token_store_path=token_store_path)

        self.logger: Logger = session_logger
        self.logger.info(
            "Web server initialized", version="1.0.0", authentication_enabled=require_auth
        )
        self._setup_routes()

    def _get_auth_dependency(self):
        """Get the appropriate auth dependency based on require_auth setting"""
        return verify_token if self.require_auth else optional_verify_token

    def _setup_routes(self):
        @self.app.get("/ping")
        async def ping():
            """
            Health check endpoint that returns the current server time.
            """
            current_time = datetime.now().isoformat()
            self.logger.debug("Ping request received", timestamp=current_time)
            return JSONResponse(
                content={"status": "ok", "timestamp": current_time, "service": "doco"}
            )

        auth_dep = self._get_auth_dependency()

        @self.app.post("/render")
        async def render_graph(
            data: GraphParams, token_info: Optional[TokenInfo] = Depends(auth_dep)
        ):
            """
            Render a graph with comprehensive error handling.
            Requires JWT authentication unless --no-auth flag is used.

            This endpoint ensures the server never crashes by catching all exceptions
            and returning appropriate HTTP error responses.
            """
            group = token_info.group if token_info else None
            datasets = data.get_datasets()
            data_points = len(datasets[0][0]) if datasets else 0

            self.logger.info(
                "Received render request",
                chart_type=data.type,
                format=data.format,
                theme=data.theme,
                num_datasets=len(datasets),
                data_points=data_points,
                group=group,
            )

            # Validate the input data
            try:
                self.logger.debug("Starting validation")
                validation_result = self.validator.validate(data)

                if not validation_result.is_valid:
                    self.logger.warning(
                        "Validation failed",
                        error_count=len(validation_result.errors),
                        errors=[e.field for e in validation_result.errors],
                    )
                    # Return detailed validation errors
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "Validation failed",
                            "message": validation_result.get_error_summary(),
                            "errors": validation_result.get_json_errors(),
                        },
                    )
            except HTTPException:
                # Re-raise HTTP exceptions
                raise
            except Exception as e:
                self.logger.error(
                    "Unexpected validation error", error=str(e), error_type=type(e).__name__
                )
                # Catch any unexpected validation errors
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Validation system error",
                        "message": f"Unexpected error during validation: {str(e)}",
                        "suggestions": [
                            "This is an internal error",
                            "Please verify your input data format",
                        ],
                    },
                )

            # Render the graph
            try:
                self.logger.debug("Starting render", group=group)
                image_data = self.renderer.render(data, group=group)
                self.logger.info(
                    "Render completed successfully",
                    chart_type=data.type,
                    format=data.format,
                    output_size=len(image_data) if isinstance(image_data, (str, bytes)) else 0,
                    group=group,
                )
            except ValueError as e:
                self.logger.error(
                    "Configuration error during render",
                    error=str(e),
                    chart_type=data.type,
                    theme=data.theme,
                )
                # Handle configuration errors (invalid type, theme, etc.)
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Configuration error",
                        "message": str(e),
                        "suggestions": [
                            "Check that the chart type is valid (line, scatter, bar)",
                            "Verify the theme name is correct (light, dark)",
                            "Ensure the format is supported (png, jpg, svg, pdf)",
                        ],
                    },
                )
            except RuntimeError as e:
                self.logger.error("Runtime error during render", error=str(e), chart_type=data.type)
                # Handle rendering errors
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Rendering failed",
                        "message": str(e),
                        "suggestions": [
                            "Verify your data values are valid numbers",
                            "Check that arrays are not empty",
                            "Try reducing the data size or simplifying the request",
                        ],
                    },
                )
            except MemoryError:
                datasets = data.get_datasets()
                data_points = len(datasets[0][0]) if datasets else 0
                self.logger.critical(
                    "Out of memory during render",
                    data_points=data_points,
                    num_datasets=len(datasets),
                    chart_type=data.type,
                )
                # Handle memory errors for large datasets
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "Request too large",
                        "message": "Not enough memory to render this graph",
                        "suggestions": [
                            "Reduce the number of data points",
                            "Use a lower resolution format",
                            "Try rendering in smaller batches",
                        ],
                    },
                )
            except Exception as e:
                self.logger.error(
                    "Unexpected error during render",
                    error=str(e),
                    error_type=type(e).__name__,
                    chart_type=data.type,
                )
                # Catch any other unexpected errors
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Unexpected rendering error",
                        "message": str(e),
                        "error_type": type(e).__name__,
                        "suggestions": [
                            "An unexpected error occurred",
                            "Please verify your input data",
                        ],
                    },
                )

            # Return the rendered image
            try:
                if data.return_base64:
                    # Ensure we have a string for base64 response
                    if isinstance(image_data, bytes):
                        image_data = image_data.decode("utf-8")
                    self.logger.debug("Returning base64 response")
                    return JSONResponse(content={"image": image_data})

                # Return image directly with appropriate content type
                media_types = {
                    "png": "image/png",
                    "jpg": "image/jpeg",
                    "svg": "image/svg+xml",
                    "pdf": "application/pdf",
                    "bmp": "image/bmp",
                }

                # Ensure we have bytes for direct response
                if isinstance(image_data, str):
                    # Check if it's a GUID (proxy mode)
                    try:
                        from uuid import UUID

                        UUID(image_data)
                        # It's a GUID, return JSON with GUID
                        self.logger.debug("Returning GUID response (proxy mode)", guid=image_data)
                        return JSONResponse(
                            content={
                                "guid": image_data,
                                "format": data.format,
                                "message": f"Image saved with GUID: {image_data}",
                                "retrieve_url": f"/render/{image_data}",
                                "html_url": f"/render/{image_data}/html",
                            }
                        )
                    except ValueError:
                        # Not a GUID, it's base64
                        image_data = base64.b64decode(image_data)

                self.logger.debug(
                    "Returning direct image response",
                    media_type=media_types.get(data.format, "image/png"),
                )
                return Response(
                    content=image_data, media_type=media_types.get(data.format, "image/png")
                )
            except Exception as e:
                self.logger.error(
                    "Failed to create response", error=str(e), error_type=type(e).__name__
                )
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Response creation failed",
                        "message": f"Failed to create HTTP response: {str(e)}",
                        "suggestions": [
                            "The image was rendered but could not be returned",
                            "Try a different output format",
                        ],
                    },
                )

        @self.app.get("/render/{guid}")
        async def get_image_by_guid(guid: str, token_info: Optional[TokenInfo] = Depends(auth_dep)):
            """
            Retrieve a rendered image by its GUID.
            Returns the raw image bytes with appropriate content type.
            Requires JWT authentication and group access (unless --no-auth is used).
            """
            group = token_info.group if token_info else None
            self.logger.info("Get image request", guid=guid, group=group)

            try:
                result = self.storage.get_image(guid, group=group)

                if result is None:
                    self.logger.warning("Image not found", guid=guid)
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "Image not found",
                            "message": f"No image found for GUID: {guid}",
                            "suggestions": [
                                "Verify the GUID is correct",
                                "The image may have been deleted",
                            ],
                        },
                    )

                image_data, img_format = result

                media_types = {
                    "png": "image/png",
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "svg": "image/svg+xml",
                    "pdf": "application/pdf",
                    "bmp": "image/bmp",
                }

                self.logger.info(
                    "Image retrieved", guid=guid, format=img_format, size=len(image_data)
                )

                return Response(
                    content=image_data,
                    media_type=media_types.get(img_format, "image/png"),
                    headers={"Content-Disposition": f'inline; filename="{guid}.{img_format}"'},
                )

            except HTTPException:
                raise
            except ValueError as e:
                self.logger.error("Invalid GUID", guid=guid, error=str(e))
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Invalid GUID",
                        "message": str(e),
                    },
                )
            except Exception as e:
                self.logger.error("Failed to retrieve image", guid=guid, error=str(e))
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Failed to retrieve image",
                        "message": str(e),
                    },
                )

        @self.app.get("/render/{guid}/html")
        async def get_image_html(guid: str, token_info: Optional[TokenInfo] = Depends(auth_dep)):
            """
            Retrieve a rendered image by its GUID and display it in an HTML page.
            Useful for viewing images directly in a browser.
            Requires JWT authentication and group access (unless --no-auth is used).
            """
            group = token_info.group if token_info else None
            self.logger.info("Get image HTML request", guid=guid, group=group)

            try:
                result = self.storage.get_image(guid, group=group)

                if result is None:
                    self.logger.warning("Image not found for HTML display", guid=guid)
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "Image not found",
                            "message": f"No image found for GUID: {guid}",
                        },
                    )

                image_data, img_format = result

                # Encode image as base64 for embedding in HTML
                base64_data = base64.b64encode(image_data).decode("utf-8")

                # Determine MIME type
                mime_types = {
                    "png": "image/png",
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "bmp": "image/bmp",
                    "svg": "image/svg+xml",
                }
                mime_type = mime_types.get(img_format, "image/png")

                # Create HTML page with embedded image
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>doco - Image {guid}</title>
                    <style>
                        body {{
                            margin: 0;
                            padding: 20px;
                            background-color: #f5f5f5;
                            font-family: Arial, sans-serif;
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                        }}
                        .container {{
                            background-color: white;
                            padding: 20px;
                            border-radius: 8px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                            max-width: 1200px;
                        }}
                        h1 {{
                            color: #333;
                            margin-top: 0;
                        }}
                        .info {{
                            color: #666;
                            margin-bottom: 20px;
                            font-size: 14px;
                        }}
                        .info code {{
                            background-color: #f0f0f0;
                            padding: 2px 6px;
                            border-radius: 3px;
                            font-family: monospace;
                        }}
                        img {{
                            max-width: 100%;
                            height: auto;
                            border: 1px solid #ddd;
                            border-radius: 4px;
                        }}
                        .links {{
                            margin-top: 20px;
                            display: flex;
                            gap: 10px;
                        }}
                        .links a {{
                            padding: 8px 16px;
                            background-color: #007bff;
                            color: white;
                            text-decoration: none;
                            border-radius: 4px;
                            font-size: 14px;
                        }}
                        .links a:hover {{
                            background-color: #0056b3;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>doco Rendered Image</h1>
                        <div class="info">
                            <strong>GUID:</strong> <code>{guid}</code><br>
                            <strong>Format:</strong> {img_format.upper()}<br>
                            <strong>Size:</strong> {len(image_data):,} bytes
                        </div>
                        <img src="data:{mime_type};base64,{base64_data}" alt="Rendered graph {guid}">
                        <div class="links">
                            <a href="/render/{guid}" download="{guid}.{img_format}">Download Image</a>
                            <a href="/ping">Server Status</a>
                        </div>
                    </div>
                </body>
                </html>
                """

                self.logger.info("HTML page generated", guid=guid, format=img_format)

                return HTMLResponse(content=html_content)

            except HTTPException:
                raise
            except ValueError as e:
                self.logger.error("Invalid GUID for HTML", guid=guid, error=str(e))
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Invalid GUID",
                        "message": str(e),
                    },
                )
            except Exception as e:
                self.logger.error("Failed to generate HTML", guid=guid, error=str(e))
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Failed to generate HTML page",
                        "message": str(e),
                    },
                )
