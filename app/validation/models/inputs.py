"""Input models for MCP server tools."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class GetTemplateDetailsInput(BaseModel):
    """Input for get_template_details.

    Args:
        template_id: Template identifier to retrieve details for
        token: Optional JWT bearer token (for authentication if required)
        group: Group context (injected from JWT token, defaults to 'public')
    """

    model_config = ConfigDict(extra="ignore")  # Ignore extra fields from MCP

    template_id: str
    token: Optional[str] = None
    group: str = "public"


class ListTemplateFragmentsInput(BaseModel):
    """Input for list_template_fragments.

    Args:
        template_id: Template identifier to list fragments for
        token: Optional JWT bearer token (for authentication if required)
        group: Group context (injected from JWT token, defaults to 'public')
    """

    model_config = ConfigDict(extra="ignore")

    template_id: str
    token: Optional[str] = None
    group: str = "public"


class GetFragmentDetailsInput(BaseModel):
    """Input for get_fragment_details.

    Args:
        template_id: Template identifier containing the fragment
        fragment_id: Fragment identifier to retrieve details for
        token: Optional JWT bearer token (for authentication if required)
        group: Group context (injected from JWT token, defaults to 'public')
    """

    model_config = ConfigDict(extra="ignore")

    template_id: str
    fragment_id: str
    token: Optional[str] = None
    group: str = "public"


class CreateDocumentSessionInput(BaseModel):
    """Input for create_document_session.

    Args:
        template_id: Template identifier to use for the new session
        alias: Friendly name for the session (3-64 chars: alphanumeric, hyphens, underscores)
        group: Group context (injected from JWT token, determines session isolation boundary)
        token: Optional JWT bearer token (required for authentication)
    """

    model_config = ConfigDict(extra="ignore")

    template_id: str
    alias: str
    group: str = "public"
    token: Optional[str] = None


class SetGlobalParametersInput(BaseModel):
    """Input for set_global_parameters.

    Args:
        session_id: Session identifier to set parameters for
        parameters: Dictionary of global parameter values
        group: Group context (injected from JWT token, used to verify session ownership)
        token: Optional JWT bearer token (required for authentication)
    """

    model_config = ConfigDict(extra="ignore")

    session_id: str
    parameters: dict
    group: str = "public"
    token: Optional[str] = None


class AddFragmentInput(BaseModel):
    """Input for add_fragment.

    Args:
        session_id: Session identifier to add fragment to
        fragment_id: Fragment identifier to instantiate
        parameters: Dictionary of fragment parameter values
        position: Optional position ('end', 'start', or index) for fragment placement
        group: Group context (injected from JWT token, used to verify session ownership)
        token: Optional JWT bearer token (required for authentication)
    """

    model_config = ConfigDict(extra="ignore")

    session_id: str
    fragment_id: str
    parameters: dict
    position: Optional[str] = None
    group: str = "public"
    token: Optional[str] = None


class AddImageFragmentInput(BaseModel):
    """Input for add_image_fragment.

    Args:
        session_id: Session identifier to add image fragment to
        image_url: URL of the image to download and display (validated at add time)
        title: Optional title/caption displayed above the image
        width: Target width in pixels (maintains aspect ratio if height not specified)
        height: Target height in pixels (maintains aspect ratio if width not specified)
        alt_text: Alternative text for accessibility (defaults to title or 'Image')
        alignment: Image alignment: 'left', 'center', 'right' (default: 'center')
        require_https: If True, only HTTPS URLs allowed (default: True for security)
        position: Optional position ('end', 'start', or guid-based) for placement
        group: Group context (injected from JWT token, used to verify session ownership)
        token: Optional JWT bearer token (required for authentication)
    """

    model_config = ConfigDict(extra="ignore")

    session_id: str
    image_url: str
    title: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    alt_text: Optional[str] = None
    alignment: str = "center"
    require_https: bool = True
    position: Optional[str] = None
    group: str = "public"
    token: Optional[str] = None


class RemoveFragmentInput(BaseModel):
    """Input for remove_fragment.

    Args:
        session_id: Session identifier to remove fragment from
        fragment_instance_guid: Unique GUID of the fragment instance to remove
        group: Group context (injected from JWT token, used to verify session ownership)
        token: Optional JWT bearer token (required for authentication)
    """

    model_config = ConfigDict(extra="ignore")

    session_id: str
    fragment_instance_guid: str
    group: str = "public"
    token: Optional[str] = None


class ListSessionFragmentsInput(BaseModel):
    """Input for list_session_fragments.

    Args:
        session_id: Session identifier to list fragments for
        group: Group context (injected from JWT token, used to verify session ownership)
        token: Optional JWT bearer token (required for authentication)
    """

    model_config = ConfigDict(extra="ignore")

    session_id: str
    group: str = "public"
    token: Optional[str] = None


class AbortDocumentSessionInput(BaseModel):
    """Input for abort_document_session.

    Args:
        session_id: Session identifier to abort and delete
        group: Group context (injected from JWT token, used to verify session ownership)
        token: Optional JWT bearer token (required for authentication)
    """

    model_config = ConfigDict(extra="ignore")

    session_id: str
    group: str = "public"
    token: Optional[str] = None


class GetSessionStatusInput(BaseModel):
    """Input for get_session_status.

    Args:
        session_id: Session identifier to check status for
        group: Group context (injected from JWT token, used to verify session ownership)
        token: Optional JWT bearer token (required for authentication)
    """

    model_config = ConfigDict(extra="ignore")

    session_id: str
    group: str = "public"
    token: Optional[str] = None


class ListActiveSessionsInput(BaseModel):
    """Input for list_active_sessions.

    Args:
        group: Group context (injected from JWT token, only sessions in this group are returned)
        token: Optional JWT bearer token (required for authentication)
    """

    model_config = ConfigDict(extra="ignore")

    group: str = "public"
    token: Optional[str] = None


class ValidateParametersInput(BaseModel):
    """Input for validate_parameters.

    Args:
        template_id: Template identifier to validate against
        parameters: Dictionary of parameter values to validate
        parameter_type: Type of parameters ('global' or 'fragment')
        fragment_id: Fragment identifier (required if parameter_type is 'fragment')
        group: Group context (injected from JWT token, used to verify template ownership)
        token: Optional JWT bearer token (required for authentication)
    """

    model_config = ConfigDict(extra="ignore")

    template_id: str
    parameters: dict
    parameter_type: str = "global"
    fragment_id: Optional[str] = None
    group: str = "public"
    token: Optional[str] = None


class GetDocumentInput(BaseModel):
    """Input for get_document."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    format: str
    style_id: Optional[str] = None
    group: str = "public"
    token: Optional[str] = None
    proxy: bool = False


class GetProxyDocumentInput(BaseModel):
    """Input for retrieving a proxied document."""

    model_config = ConfigDict(extra="ignore")

    proxy_guid: str
    token: Optional[str] = None
