"""Doco Web Server - REST API for document discovery and rendering.

Minimal web server that exposes:
- Discovery endpoints (templates, fragments, styles metadata)
- get_document endpoint (render pre-built sessions or proxy retrieval)

Does NOT implement session lifecycle - use MCP server for session workflows.
Authentication via X-Auth-Token header (group:token format) or Authorization Bearer.
"""

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse, Response
from app.rendering.engine import RenderingEngine
from app.templates.registry import TemplateRegistry
from app.fragments.registry import FragmentRegistry
from app.styles.registry import StyleRegistry
from app.sessions import SessionManager, SessionStore
from app.validation.document_models import OutputFormat
from app.logger import Logger, session_logger
from app.config import get_default_sessions_dir
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class DocoWebServer:
    """FastAPI web server for document discovery and rendering only."""

    def __init__(
        self,
        templates_dir: Optional[str] = None,
        fragments_dir: Optional[str] = None,
        styles_dir: Optional[str] = None,
        styles_group: str = "public",
        require_auth: bool = True,
        auth_service: Optional[Any] = None,
    ):
        """
        Initialize the Doco web server.

        Args:
            templates_dir: Templates directory path
            fragments_dir: Fragments directory path
            styles_dir: Styles directory path
            styles_group: Default styles group
            require_auth: Whether to require authentication via X-Auth-Token header
            auth_service: AuthService instance for token verification (required if require_auth=True)

        Endpoints exposed:
            GET /ping - Health check
            GET /templates - List templates
            GET /templates/{id} - Template details
            GET /templates/{id}/fragments - Template fragments list
            GET /fragments/{id} - Fragment details
            GET /styles - List styles
            POST /render/{session_id} - Render finalized session or proxy document
        """
        self.app = FastAPI(title="doco", description="Document discovery and rendering REST API")

        # Set up registries
        project_root = Path(__file__).parent.parent
        self.templates_dir = templates_dir or str(project_root / "data" / "docs" / "templates")
        self.fragments_dir = fragments_dir or str(project_root / "data" / "docs" / "fragments")
        self.styles_dir = styles_dir or str(project_root / "data" / "docs" / "styles")
        self.styles_group = styles_group

        self.template_registry = TemplateRegistry(self.templates_dir, session_logger)
        self.fragment_registry = FragmentRegistry(self.fragments_dir, session_logger)
        self.style_registry = StyleRegistry(
            self.styles_dir, logger=session_logger, group=styles_group
        )

        # Set up session manager for loading finalized sessions
        self.session_store = SessionStore(
            base_dir=get_default_sessions_dir(), logger=session_logger
        )
        self.session_manager = SessionManager(
            session_store=self.session_store,
            template_registry=self.template_registry,
            logger=session_logger,
        )

        # Set up rendering engine
        self.engine = RenderingEngine(
            template_registry=self.template_registry,
            style_registry=self.style_registry,
            logger=session_logger,
        )

        self.require_auth = require_auth
        self.auth_service = auth_service
        self.logger: Logger = session_logger

        self.logger.info(
            "Doco web server initialized",
            templates_dir=self.templates_dir,
            fragments_dir=self.fragments_dir,
            styles_dir=self.styles_dir,
            authentication_required=require_auth,
            endpoints=["discovery", "get_document"],
        )
        self._setup_routes()

    def _extract_auth_group(self, authorization: Optional[str]) -> Optional[str]:
        """
        Extract group from X-Auth-Token header or Authorization Bearer header.

        Header formats:
        - X-Auth-Token: <group>:<token>
        - Authorization: Bearer <token> (token must be a JWT containing group)

        Args:
            authorization: Header value

        Returns:
            Group name if auth provided, None otherwise
        """
        if not authorization:
            return None

        try:
            # Check for X-Auth-Token format: "group:token"
            if ":" in authorization and not authorization.startswith("Bearer "):
                parts = authorization.split(":", 1)
                if len(parts) == 2:
                    return parts[0]

            # Check for Bearer format: extract group from JWT token
            if authorization.startswith("Bearer "):
                token = authorization[7:]  # Remove "Bearer " prefix
                if self.auth_service:
                    try:
                        token_info = self.auth_service.verify_token(token)
                        return token_info.group
                    except Exception:
                        # Token is invalid, return None
                        pass
        except Exception:
            pass

        return None

    def _verify_auth_header(
        self, x_auth_token: Optional[str], authorization: Optional[str]
    ) -> Optional[str]:
        """
        Verify authentication header and return group.

        Supports both X-Auth-Token (legacy) and Authorization: Bearer (standard) headers.

        Args:
            x_auth_token: X-Auth-Token header value (legacy format: group:token)
            authorization: Authorization header value (standard format: Bearer token)

        Returns:
            Group name if auth valid, raises HTTPException if required but missing
        """
        # Prefer X-Auth-Token if provided, fall back to Authorization
        auth_header = x_auth_token or authorization

        if self.require_auth:
            if not auth_header:
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "AUTHENTICATION_REQUIRED",
                        "message": "Authentication required. Use either X-Auth-Token or Authorization header.",
                        "formats": [
                            "X-Auth-Token: <group>:<token>",
                            "Authorization: Bearer <token>",
                        ],
                    },
                )

        return self._extract_auth_group(auth_header)

    def _setup_routes(self):
        """Set up all API routes for discovery and document rendering."""

        # ====================================================================
        # DISCOVERY ENDPOINTS (no auth required)
        # ====================================================================

        @self.app.get("/ping")
        async def ping():
            """
            Health check endpoint.

            Returns:
                {status: "ok", timestamp: ISO8601, service: "doco"}
            """
            current_time = datetime.now().isoformat()
            self.logger.info("GET /ping", timestamp=current_time)
            result = JSONResponse(
                content={"status": "ok", "timestamp": current_time, "service": "doco"}
            )
            self.logger.info("/ping completed", status=200)
            return result

        @self.app.get("/templates")
        async def list_templates(group: Optional[str] = None):
            """List available templates."""
            self.logger.info("GET /templates", group=group or "(all)")
            try:
                templates = self.template_registry.list_templates(group=group)
                self.logger.info("/templates completed", count=len(templates), status=200)
                return JSONResponse(
                    content={
                        "status": "success",
                        "data": [
                            {
                                "template_id": t.template_id,
                                "name": t.name,
                                "description": t.description,
                                "group": t.group,
                            }
                            for t in templates
                        ],
                    }
                )
            except Exception as e:
                self.logger.error(
                    "/templates failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    status=500,
                )
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/templates/{template_id}")
        async def get_template_details(template_id: str):
            """Get detailed information about a template."""
            self.logger.info("GET /templates/{id}", template_id=template_id)
            try:
                details = self.template_registry.get_template_details(template_id)
                if not details:
                    self.logger.warning("Template not found", template_id=template_id, status=404)
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "TEMPLATE_NOT_FOUND",
                            "message": f"Template '{template_id}' not found",
                        },
                    )

                return JSONResponse(
                    content={
                        "status": "success",
                        "data": {
                            "template_id": details.template_id,
                            "name": details.name,
                            "description": details.description,
                            "group": details.group,
                            "global_parameters": [
                                {
                                    "name": p.get("name") if isinstance(p, dict) else p.name,
                                    "type": p.get("type") if isinstance(p, dict) else p.type,
                                    "description": (
                                        p.get("description")
                                        if isinstance(p, dict)
                                        else p.description
                                    ),
                                    "required": (
                                        p.get("required", True)
                                        if isinstance(p, dict)
                                        else p.required
                                    ),
                                    "default": (
                                        p.get("default") if isinstance(p, dict) else p.default
                                    ),
                                }
                                for p in details.global_parameters
                            ],
                        },
                    }
                )
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error getting template details: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/templates/{template_id}/fragments")
        async def list_template_fragments(template_id: str):
            """List fragments available in a template."""
            self.logger.info("List template fragments request", template_id=template_id)
            try:
                template = self.template_registry.get_template_details(template_id)
                if not template:
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "TEMPLATE_NOT_FOUND",
                            "message": f"Template '{template_id}' not found",
                        },
                    )

                fragments = self.fragment_registry.list_fragments()
                return JSONResponse(
                    content={
                        "status": "success",
                        "data": [
                            {
                                "fragment_id": f["fragment_id"],
                                "name": f["name"],
                                "description": f["description"],
                                "group": f["group"],
                            }
                            for f in fragments
                        ],
                    }
                )
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error listing fragments: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/fragments/{fragment_id}")
        async def get_fragment_details(fragment_id: str, template_id: Optional[str] = None):
            """Get detailed information about a fragment."""
            self.logger.info(
                "Get fragment details request", fragment_id=fragment_id, template_id=template_id
            )
            try:
                schema = self.fragment_registry.get_fragment_schema(fragment_id)
                if not schema:
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "FRAGMENT_NOT_FOUND",
                            "message": f"Fragment '{fragment_id}' not found",
                        },
                    )

                return JSONResponse(
                    content={
                        "status": "success",
                        "data": {
                            "fragment_id": schema.fragment_id,
                            "name": schema.name,
                            "description": schema.description,
                            "group": schema.group,
                            "parameters": [
                                {
                                    "name": p.name,
                                    "type": p.type,
                                    "description": p.description,
                                    "required": p.required,
                                    "default": p.default,
                                }
                                for p in schema.parameters
                            ],
                        },
                    }
                )
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error getting fragment details: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/styles")
        async def list_styles(group: Optional[str] = None):
            """List available styles."""
            self.logger.info("List styles request", group=group)
            try:
                styles = self.style_registry.list_styles(group=group)
                return JSONResponse(
                    content={
                        "status": "success",
                        "data": [
                            {
                                "style_id": s.style_id,
                                "name": s.name,
                                "description": s.description,
                                "group": s.group,
                            }
                            for s in styles
                        ],
                    }
                )
            except Exception as e:
                self.logger.error(f"Error listing styles: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        # ====================================================================
        # DOCUMENT RENDERING ENDPOINT (auth required via X-Auth-Token header)
        # ====================================================================
        # NOTE: Web server only renders pre-finalized sessions.
        # Use MCP server for full session lifecycle (create, add fragments, etc.)

        @self.app.post("/render/{session_id}")
        async def get_document(
            session_id: str,
            request: Request,
            body: Optional[Dict[str, Any]] = None,
            x_auth_token: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None),
        ):
            """
            Render a finalized document session to the specified format.

            Path parameter:
            - session_id: Session identifier - can be either session alias (e.g., 'my-report-2025')
                         or session UUID. Aliases are easier to use and remember.

            Request body should contain:
            - format: Output format (html, markdown, pdf). Default: html
            - style_id: Optional style ID override
            - proxy: Optional bool - if true, store on server and return GUID instead of content

            Returns:
            - HTML format: Response with media_type="text/html"
            - PDF format: Response with media_type="application/pdf"
            - Markdown format: Response with media_type="text/markdown"
            - Proxy mode: JSON with proxy_guid field
            """
            auth_group = self._verify_auth_header(x_auth_token, authorization)

            if body is None:
                body = {}

            output_format = body.get("format", "html").lower()
            style_id = body.get("style_id")
            proxy = body.get("proxy", False)

            self.logger.info(
                "POST /render/{id}",
                session_id=session_id,
                format=output_format,
                proxy=proxy,
                auth_group=auth_group,
                style_id=style_id or "(default)",
            )

            try:
                # Resolve alias to GUID if needed
                resolved_session_id = self.session_manager.resolve_session(
                    auth_group or "public", session_id
                )
                if not resolved_session_id:
                    # If not found as alias, try as direct GUID
                    if self.session_manager._is_valid_uuid(session_id):
                        resolved_session_id = session_id
                    else:
                        raise HTTPException(
                            status_code=404,
                            detail={
                                "error": "SESSION_NOT_FOUND",
                                "message": f"Session '{session_id}' not found. Use session alias or UUID.",
                            },
                        )

                # Get the session
                session = await self.session_manager.get_session(resolved_session_id)
                if not session:
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "SESSION_NOT_FOUND",
                            "message": f"Session '{session_id}' not found",
                        },
                    )

                # Verify group access if auth_group is set
                if auth_group and session.group != auth_group:
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": "ACCESS_DENIED",
                            "message": f"Access denied to group '{session.group}'",
                        },
                    )

                # Render the document
                output_format_obj = OutputFormat(output_format)
                output_obj = await self.engine.render_document(
                    session=session, output_format=output_format_obj, style_id=style_id, proxy=proxy
                )

                self.logger.info(
                    "/render completed successfully",
                    session_id=resolved_session_id,
                    session_alias=session_id if session_id != resolved_session_id else None,
                    format=output_format,
                    proxy=proxy,
                    proxy_guid=output_obj.proxy_guid if proxy else None,
                    output_size=len(output_obj.content) if output_obj.content else 0,
                    status=200,
                )

                # Return appropriate response based on format and proxy mode
                if proxy:
                    # Proxy mode: return GUID and download URL instead of content
                    download_url = f"{request.url.scheme}://{request.headers.get('host', 'localhost:8000')}/proxy/{output_obj.proxy_guid}"
                    return JSONResponse(
                        content={
                            "status": "success",
                            "data": {
                                "proxy_guid": output_obj.proxy_guid,
                                "download_url": download_url,
                                "format": output_format,
                                "message": "Document stored in proxy mode. Use download_url to retrieve the document.",
                            },
                        }
                    )
                else:
                    # Direct render: return content with appropriate media type
                    if output_format_obj == OutputFormat.HTML:
                        return Response(content=output_obj.content, media_type="text/html")
                    elif output_format_obj in (OutputFormat.MARKDOWN, OutputFormat.MD):
                        return Response(content=output_obj.content, media_type="text/markdown")
                    elif output_format_obj == OutputFormat.PDF:
                        return Response(content=output_obj.content, media_type="application/pdf")
                    else:
                        # Fallback: return as JSON
                        return JSONResponse(
                            content={
                                "status": "success",
                                "data": {"format": output_format, "content": output_obj.content},
                            }
                        )

            except HTTPException as e:
                self.logger.error(
                    "/render failed (HTTP)",
                    session_identifier=session_id,
                    status_code=e.status_code,
                    detail=str(e.detail),
                )
                raise
            except ValueError as e:
                self.logger.error(
                    "/render failed (validation)",
                    session_identifier=session_id,
                    error=str(e),
                    error_type="ValueError",
                    status=400,
                )
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                self.logger.error(
                    "/render failed (unexpected)",
                    session_identifier=session_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    status=500,
                )
                raise HTTPException(status_code=500, detail=str(e))

        # ====================================================================
        # PROXY DOCUMENT RETRIEVAL ENDPOINT
        # ====================================================================

        @self.app.get("/proxy/{proxy_guid}")
        async def get_proxy_document(
            proxy_guid: str,
            x_auth_token: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None),
        ):
            """
            Retrieve a previously stored proxy document.

            Args:
                proxy_guid: The proxy document GUID
                x_auth_token: Optional authentication token (X-Auth-Token format)
                authorization: Optional authentication token (Bearer format)

            Returns:
                Document content with appropriate media type based on format

            Note:
                Group ownership is verified against the stored group metadata in the proxy
                document, not from URL parameters. This prevents group parameter injection attacks.
            """
            auth_group = self._verify_auth_header(x_auth_token, authorization)

            self.logger.info(
                "GET /proxy/{guid}", proxy_guid=proxy_guid, auth_group=auth_group or "(none)"
            )

            try:
                # Retrieve the proxy document (reads stored group from metadata)
                output_obj = await self.engine.get_proxy_document(proxy_guid)
                stored_group = output_obj.group

                self.logger.info(
                    "Proxy document retrieved",
                    proxy_guid=proxy_guid,
                    stored_group=stored_group,
                    auth_group=auth_group,
                )

                # Verify group access: auth token group must match stored group
                if auth_group and stored_group != auth_group:
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": "ACCESS_DENIED",
                            "message": f"Access denied: document belongs to group '{stored_group}', token is for group '{auth_group}'",
                        },
                    )

                self.logger.info(
                    "Proxy document retrieved successfully",
                    proxy_guid=proxy_guid,
                    group=stored_group,
                    format=output_obj.format.value,
                    size=len(output_obj.content) if output_obj.content else 0,
                )

                # Return content with appropriate media type
                if output_obj.format == OutputFormat.HTML:
                    return Response(content=output_obj.content, media_type="text/html")
                elif output_obj.format in (OutputFormat.MARKDOWN, OutputFormat.MD):
                    return Response(content=output_obj.content, media_type="text/markdown")
                elif output_obj.format == OutputFormat.PDF:
                    return Response(content=output_obj.content, media_type="application/pdf")
                else:
                    # Fallback: return as text
                    return Response(content=output_obj.content, media_type="text/plain")

            except HTTPException:
                raise
            except ValueError as e:
                # ValueError from engine indicates document not found
                error_msg = str(e)
                if "not found" in error_msg.lower():
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "PROXY_NOT_FOUND",
                            "message": error_msg,
                        },
                    )
                else:
                    raise HTTPException(status_code=400, detail=error_msg)
            except Exception as e:
                self.logger.error(f"Error retrieving proxy document: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "RETRIEVAL_ERROR",
                        "message": f"Failed to retrieve proxy document: {str(e)}",
                    },
                )
