"""Doco Web Server - Document rendering REST API."""
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, Response
from app.rendering.engine import RenderingEngine
from app.templates.registry import TemplateRegistry
from app.fragments.registry import FragmentRegistry
from app.styles.registry import StyleRegistry
from app.validation.document_models import DocumentSession, OutputFormat
from app.validation import Validator
from app.storage.file_storage import FileStorage
from app.auth import TokenInfo, verify_token, optional_verify_token, init_auth_service
from app.logger import Logger, session_logger
from app.config import Config
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import uuid


class DocoWebServer:
    """FastAPI web server for document rendering with group support."""

    def __init__(
        self,
        templates_dir: Optional[str] = None,
        fragments_dir: Optional[str] = None,
        styles_dir: Optional[str] = None,
        jwt_secret: Optional[str] = None,
        token_store_path: Optional[str] = None,
        require_auth: bool = True,
    ):
        """
        Initialize the Doco web server.

        Args:
            templates_dir: Templates directory path
            fragments_dir: Fragments directory path
            styles_dir: Styles directory path
            jwt_secret: JWT secret for authentication
            token_store_path: Path to token store file
            require_auth: Whether to require authentication
        """
        self.app = FastAPI(
            title="doco",
            description="Document rendering service with template and fragment support"
        )

        # Set up registries
        project_root = Path(__file__).parent.parent
        self.templates_dir = templates_dir or str(project_root / "templates")
        self.fragments_dir = fragments_dir or str(project_root / "fragments")
        self.styles_dir = styles_dir or str(project_root / "styles")

        self.template_registry = TemplateRegistry(self.templates_dir, session_logger)
        self.fragment_registry = FragmentRegistry(self.fragments_dir, session_logger)
        self.style_registry = StyleRegistry(self.styles_dir, session_logger)
        self.storage = FileStorage(str(Config.get_storage_dir()))

        # Set up rendering engine
        self.engine = RenderingEngine(
            self.template_registry,
            self.style_registry,
            session_logger
        )

        # Set up validator
        self.validator = Validator()

        self.require_auth = require_auth
        self.logger: Logger = session_logger

        # Initialize auth service only if auth is required
        if require_auth:
            init_auth_service(secret_key=jwt_secret, token_store_path=token_store_path)

        self.logger.info(
            "Doco web server initialized",
            templates_dir=self.templates_dir,
            fragments_dir=self.fragments_dir,
            styles_dir=self.styles_dir,
            authentication_enabled=require_auth
        )
        self._setup_routes()

    def _get_auth_dependency(self):
        """Get the appropriate auth dependency based on require_auth setting."""
        return verify_token if self.require_auth else optional_verify_token

    def _setup_routes(self):
        """Set up all API routes."""

        @self.app.get("/ping")
        async def ping():
            """Health check endpoint."""
            current_time = datetime.now().isoformat()
            self.logger.debug("Ping request received", timestamp=current_time)
            return JSONResponse(
                content={"status": "ok", "timestamp": current_time, "service": "doco"}
            )

        auth_dep = self._get_auth_dependency()

        @self.app.get("/templates")
        async def list_templates(
            group: Optional[str] = None,
            token_info: Optional[TokenInfo] = Depends(auth_dep)
        ):
            """List available templates."""
            self.logger.info("List templates request", group=group)
            try:
                templates = self.template_registry.list_templates(group=group)
                return JSONResponse(
                    content={
                        "templates": [
                            {
                                "template_id": t.template_id,
                                "name": t.name,
                                "description": t.description,
                                "group": t.group,
                            }
                            for t in templates
                        ]
                    }
                )
            except Exception as e:
                self.logger.error(f"Error listing templates: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/templates/{template_id}")
        async def get_template_details(
            template_id: str,
            token_info: Optional[TokenInfo] = Depends(auth_dep)
        ):
            """Get detailed information about a template."""
            self.logger.info("Get template details request", template_id=template_id)
            try:
                details = self.template_registry.get_template_details(template_id)
                if not details:
                    raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

                return JSONResponse(
                    content={
                        "template_id": details.template_id,
                        "name": details.name,
                        "description": details.description,
                        "group": details.group,
                        "global_parameters": [
                            {
                                "name": p.get("name") if isinstance(p, dict) else p.name,
                                "type": p.get("type") if isinstance(p, dict) else p.type,
                                "description": p.get("description") if isinstance(p, dict) else p.description,
                                "required": p.get("required", True) if isinstance(p, dict) else p.required,
                                "default": p.get("default") if isinstance(p, dict) else p.default,
                            }
                            for p in details.global_parameters
                        ],
                    }
                )
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error getting template details: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/fragments")
        async def list_fragments(
            group: Optional[str] = None,
            token_info: Optional[TokenInfo] = Depends(auth_dep)
        ):
            """List available standalone fragments."""
            self.logger.info("List fragments request", group=group)
            try:
                fragments = self.fragment_registry.list_fragments(group=group)
                return JSONResponse(
                    content={
                        "fragments": [
                            {
                                "fragment_id": f["fragment_id"],
                                "name": f["name"],
                                "description": f["description"],
                                "group": f["group"],
                            }
                            for f in fragments
                        ]
                    }
                )
            except Exception as e:
                self.logger.error(f"Error listing fragments: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/styles")
        async def list_styles(
            group: Optional[str] = None,
            token_info: Optional[TokenInfo] = Depends(auth_dep)
        ):
            """List available styles."""
            self.logger.info("List styles request", group=group)
            try:
                styles = self.style_registry.list_styles(group=group)
                return JSONResponse(
                    content={
                        "styles": [
                            {
                                "style_id": s.style_id,
                                "name": s.name,
                                "description": s.description,
                                "group": s.group,
                            }
                            for s in styles
                        ]
                    }
                )
            except Exception as e:
                self.logger.error(f"Error listing styles: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/groups")
        async def list_groups(
            token_info: Optional[TokenInfo] = Depends(auth_dep)
        ):
            """List all available groups across templates, fragments, and styles."""
            self.logger.info("List groups request")
            try:
                all_groups = set()
                all_groups.update(self.template_registry.list_groups())
                all_groups.update(self.fragment_registry.list_groups())
                all_groups.update(self.style_registry.list_groups())

                return JSONResponse(
                    content={"groups": sorted(list(all_groups))}
                )
            except Exception as e:
                self.logger.error(f"Error listing groups: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/validate")
        async def validate_document(
            request_body: Dict[str, Any],
            token_info: Optional[TokenInfo] = Depends(auth_dep)
        ):
            """
            Validate a document against its template.
            
            Request body should contain:
            - template_id: The template to validate against
            - group: The group (mandatory)
            - parameters: Global template parameters
            - fragments: List of fragments in the document
            """
            group = token_info.group if token_info else None
            template_id = request_body.get("template_id")
            
            self.logger.info(
                "Validation request",
                template_id=template_id,
                group=group
            )

            try:
                # Create document session
                session_id = str(uuid.uuid4())
                now = datetime.now().isoformat()
                
                final_group = group or request_body.get("group")
                if not final_group:
                    raise ValueError("group is required")
                if not template_id:
                    raise ValueError("template_id is required")
                
                session = DocumentSession(
                    session_id=session_id,
                    template_id=template_id,
                    created_at=now,
                    updated_at=now,
                    group=final_group,
                    global_parameters=request_body.get("parameters", {}),
                    fragments=request_body.get("fragments", [])
                )

                # Validate the document
                validation_result = self.validator.validate(session)

                if not validation_result.is_valid:
                    self.logger.warning(
                        "Validation failed",
                        template_id=session.template_id,
                        error_count=len(validation_result.errors)
                    )
                    return JSONResponse(
                        status_code=400,
                        content={
                            "valid": False,
                            "error_summary": validation_result.get_error_summary(),
                            "errors": validation_result.get_json_errors(),
                        }
                    )

                self.logger.info(
                    "Validation passed",
                    template_id=session.template_id
                )
                return JSONResponse(
                    content={"valid": True, "message": "Document is valid"}
                )

            except ValueError as e:
                self.logger.error(f"Invalid request: {str(e)}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                self.logger.error(f"Validation error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/render")
        async def render_document(
            request_body: Dict[str, Any],
            format: str = Query("html", description="Output format: html, markdown, or pdf"),
            token_info: Optional[TokenInfo] = Depends(auth_dep)
        ):
            """
            Render a document to the specified format.
            
            Request body should contain:
            - template_id: The template to render
            - group: The group (mandatory)
            - style_id: Optional style to apply
            - parameters: Global template parameters
            - fragments: List of fragments in the document
            """
            group = token_info.group if token_info else None
            template_id = request_body.get("template_id")

            self.logger.info(
                "Render request",
                template_id=template_id,
                format=format,
                group=group
            )

            try:
                # Create document session
                session_id = str(uuid.uuid4())
                now = datetime.now().isoformat()
                
                final_group = group or request_body.get("group")
                if not final_group:
                    raise ValueError("group is required")
                if not template_id:
                    raise ValueError("template_id is required")
                
                session = DocumentSession(
                    session_id=session_id,
                    template_id=template_id,
                    created_at=now,
                    updated_at=now,
                    group=final_group,
                    global_parameters=request_body.get("parameters", {}),
                    fragments=request_body.get("fragments", [])
                )

                # Validate the document
                validation_result = self.validator.validate(session)
                if not validation_result.is_valid:
                    self.logger.warning(
                        "Validation failed before render",
                        template_id=template_id,
                        error_count=len(validation_result.errors)
                    )
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": "Validation failed",
                            "error_summary": validation_result.get_error_summary(),
                            "errors": validation_result.get_json_errors(),
                        }
                    )

                # Render the document
                output_format = OutputFormat(format.lower())
                style_id = request_body.get("style_id")
                output_obj = await self.engine.render_document(session, output_format, style_id)
                output = output_obj.content

                self.logger.info(
                    "Render completed",
                    template_id=template_id,
                    format=format,
                    output_size=len(output) if output else 0
                )

                # Return appropriate response based on format
                if output_format == OutputFormat.HTML:
                    return Response(content=output, media_type="text/html")
                elif output_format in (OutputFormat.MARKDOWN, OutputFormat.MD):
                    return Response(content=output, media_type="text/markdown")
                elif output_format == OutputFormat.PDF:
                    return Response(content=output, media_type="application/pdf")
                else:
                    return JSONResponse(
                        content={"output": output}
                    )

            except ValueError as e:
                self.logger.error(f"Invalid request: {str(e)}")
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                self.logger.error(f"Rendering error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
