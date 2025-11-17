"""Document generation validation models using Pydantic v2."""

from typing import List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class ParameterSchema:
    """Schema for a single parameter in templates or fragments."""

    name: str
    type: str  # string, integer, number, boolean, array, object
    description: str
    required: bool = True
    default: Optional[Any] = None
    example: Optional[Any] = None
    group: str = "public"  # Parameters inherit group from parent (template/fragment/style)


@dataclass
class TemplateMetadata:
    """Metadata for a template."""

    template_id: str
    group: str  # NEW: Mandatory group field (must match directory location)
    name: str
    description: str
    version: str = "1.0.0"


@dataclass
class FragmentSchema:
    """Schema for a reusable fragment."""

    fragment_id: str
    group: str  # NEW: Mandatory group field (must match directory location)
    name: str
    description: str
    parameters: List[ParameterSchema] = field(default_factory=list)


@dataclass
class TemplateSchema:
    """Complete template schema with metadata and fragments."""

    metadata: TemplateMetadata
    global_parameters: List[ParameterSchema] = field(default_factory=list)
    fragments: List[FragmentSchema] = field(default_factory=list)


@dataclass
class StyleSchema:
    """Schema for a style asset."""

    style_id: str
    group: str  # NEW: Mandatory group field (must match directory location)
    name: str
    description: str
    parameters: List[ParameterSchema] = field(default_factory=list)


class TemplateListItem:
    """Template item for discovery responses."""

    def __init__(self, template_id: str, name: str, description: str, group: str):
        self.template_id = template_id
        self.name = name
        self.description = description
        self.group = group  # Mandatory - comes from loaded template metadata


class TemplateDetailsOutput:
    """Template details including parameters."""

    def __init__(
        self,
        template_id: str,
        name: str,
        description: str,
        group: str,
        global_parameters: Optional[List[dict]] = None,
    ):
        self.template_id = template_id
        self.name = name
        self.description = description
        self.group = group  # Mandatory - comes from template metadata
        self.global_parameters = global_parameters or []


class FragmentInstance:
    """A fragment instance in a document session."""

    def __init__(
        self,
        fragment_id: str,
        parameters: Optional[dict] = None,
        fragment_instance_guid: Optional[str] = None,
        created_at: Optional[str] = None,
    ):
        self.fragment_id = fragment_id
        self.parameters = parameters or {}
        self.fragment_instance_guid = fragment_instance_guid
        self.created_at = created_at


class DocumentSession:
    """Active document session state."""

    def __init__(
        self,
        session_id: str,
        template_id: str,
        created_at: str,
        updated_at: str,
        group: str,  # Mandatory - comes from template metadata
        global_parameters: Optional[dict] = None,
        fragments: Optional[List[dict]] = None,
    ):
        self.session_id = session_id
        self.template_id = template_id
        self.group = group  # Mandatory - track group context in session
        self.global_parameters = global_parameters or {}

        # Convert dict fragments to FragmentInstance objects
        self.fragments = []
        if fragments:
            for frag in fragments:
                if isinstance(frag, dict):
                    frag_id = frag.get("fragment_id")
                    if frag_id:
                        self.fragments.append(
                            FragmentInstance(
                                fragment_id=frag_id,
                                parameters=frag.get("parameters", {}),
                                fragment_instance_guid=frag.get("fragment_instance_guid"),
                                created_at=frag.get("created_at"),
                            )
                        )
                elif isinstance(frag, FragmentInstance):
                    self.fragments.append(frag)

        self.created_at = created_at
        self.updated_at = updated_at


class OutputFormat(str, Enum):
    """Supported output formats for document rendering."""

    HTML = "html"
    PDF = "pdf"
    MARKDOWN = "markdown"
    MD = "markdown"  # Alias


class GetDocumentOutput:
    """Output from document rendering."""

    def __init__(
        self,
        session_id: str,
        format: OutputFormat,
        style_id: str,
        content: str,
        message: str,
        proxy_guid: Optional[str] = None,
    ):
        self.session_id = session_id
        self.format = format
        self.style_id = style_id
        self.content = content
        self.message = message
        self.proxy_guid = proxy_guid


class CreateSessionOutput:
    """Output from creating a new document session."""

    def __init__(self, session_id: str, template_id: str, created_at: str):
        self.session_id = session_id
        self.template_id = template_id
        self.created_at = created_at


class SetGlobalParametersOutput:
    """Output from setting global parameters."""

    def __init__(self, session_id: str, message: str):
        self.session_id = session_id
        self.message = message


class SessionFragmentInfo:
    """Information about a fragment instance in a session."""

    def __init__(
        self,
        fragment_instance_guid: str,
        fragment_id: str,
        fragment_name: str,
        position: int,
        parameters: Optional[dict] = None,
    ):
        self.fragment_instance_guid = fragment_instance_guid
        self.fragment_id = fragment_id
        self.fragment_name = fragment_name
        self.position = position
        self.parameters = parameters or {}


class AddFragmentOutput:
    """Output from adding a fragment to a session."""

    def __init__(
        self,
        session_id: str,
        fragment_instance_guid: str,
        fragment_id: str,
        position: int,
        message: str,
    ):
        self.session_id = session_id
        self.fragment_instance_guid = fragment_instance_guid
        self.fragment_id = fragment_id
        self.position = position
        self.message = message


class RemoveFragmentOutput:
    """Output from removing a fragment from a session."""

    def __init__(self, session_id: str, fragment_instance_guid: str, message: str):
        self.session_id = session_id
        self.fragment_instance_guid = fragment_instance_guid
        self.message = message


class ListSessionFragmentsOutput:
    """Output from listing fragments in a session."""

    def __init__(self, session_id: str, fragment_count: int, fragments: Optional[List] = None):
        self.session_id = session_id
        self.fragment_count = fragment_count
        self.fragments = fragments or []


class AbortSessionOutput:
    """Output from aborting a session."""

    def __init__(self, session_id: str, message: str):
        self.session_id = session_id
        self.message = message


# ============================================================================
# Input Models for MCP Server
# ============================================================================


class GetTemplateDetailsInput:
    """Input for get_template_details."""

    def __init__(self, template_id: str, token: Optional[str] = None):
        self.template_id = template_id
        self.token = token

    @classmethod
    def model_validate(cls, data: dict):
        return cls(**data)


class ListTemplateFragmentsInput:
    """Input for list_template_fragments."""

    def __init__(self, template_id: str, token: Optional[str] = None):
        self.template_id = template_id
        self.token = token

    @classmethod
    def model_validate(cls, data: dict):
        return cls(**data)


class GetFragmentDetailsInput:
    """Input for get_fragment_details."""

    def __init__(self, template_id: str, fragment_id: str, token: Optional[str] = None):
        self.template_id = template_id
        self.fragment_id = fragment_id
        self.token = token

    @classmethod
    def model_validate(cls, data: dict):
        return cls(**data)


class CreateDocumentSessionInput:
    """Input for create_document_session."""

    def __init__(self, template_id: str, group: str = "public", token: Optional[str] = None):
        self.template_id = template_id
        self.group = group
        self.token = token

    @classmethod
    def model_validate(cls, data: dict):
        return cls(**data)


class SetGlobalParametersInput:
    """Input for set_global_parameters."""

    def __init__(self, session_id: str, parameters: dict, token: Optional[str] = None):
        self.session_id = session_id
        self.parameters = parameters
        self.token = token

    @classmethod
    def model_validate(cls, data: dict):
        return cls(**data)


class AddFragmentInput:
    """Input for add_fragment."""

    def __init__(
        self,
        session_id: str,
        fragment_id: str,
        parameters: dict,
        position: Optional[str] = None,
        token: Optional[str] = None,
    ):
        self.session_id = session_id
        self.fragment_id = fragment_id
        self.parameters = parameters
        self.position = position
        self.token = token

    @classmethod
    def model_validate(cls, data: dict):
        return cls(**data)


class RemoveFragmentInput:
    """Input for remove_fragment."""

    def __init__(self, session_id: str, fragment_instance_guid: str, token: Optional[str] = None):
        self.session_id = session_id
        self.fragment_instance_guid = fragment_instance_guid
        self.token = token

    @classmethod
    def model_validate(cls, data: dict):
        return cls(**data)


class ListSessionFragmentsInput:
    """Input for list_session_fragments."""

    def __init__(self, session_id: str, token: Optional[str] = None):
        self.session_id = session_id
        self.token = token

    @classmethod
    def model_validate(cls, data: dict):
        return cls(**data)


class AbortDocumentSessionInput:
    """Input for abort_document_session."""

    def __init__(self, session_id: str, token: Optional[str] = None):
        self.session_id = session_id
        self.token = token

    @classmethod
    def model_validate(cls, data: dict):
        return cls(**data)


class GetDocumentInput:
    """Input for get_document."""

    def __init__(
        self,
        session_id: str,
        format: str,
        style_id: Optional[str] = None,
        token: Optional[str] = None,
        proxy: Optional[bool] = False,
    ):
        self.session_id = session_id
        self.format = format
        self.style_id = style_id
        self.token = token
        self.proxy = proxy or False

    @classmethod
    def model_validate(cls, data: dict):
        return cls(**data)


# ============================================================================
# Additional Output Models for MCP Server
# ============================================================================


class PingOutput:
    """Output from ping."""

    def __init__(self, status: str, timestamp: str, message: str):
        self.status = status
        self.timestamp = timestamp
        self.message = message

    def model_dump(self, mode: str = "json") -> dict:
        return {
            "status": self.status,
            "timestamp": self.timestamp,
            "message": self.message,
        }


class FragmentListItem:
    """Fragment item in template discovery."""

    def __init__(self, fragment_id: str, name: str, description: str, parameter_count: int):
        self.fragment_id = fragment_id
        self.name = name
        self.description = description
        self.parameter_count = parameter_count

    def model_dump(self, mode: str = "json") -> dict:
        return {
            "fragment_id": self.fragment_id,
            "name": self.name,
            "description": self.description,
            "parameter_count": self.parameter_count,
        }


class FragmentDetailsOutput:
    """Detailed information about a fragment."""

    def __init__(
        self,
        template_id: str,
        fragment_id: str,
        name: str,
        description: str,
        parameters: Optional[List] = None,
    ):
        self.template_id = template_id
        self.fragment_id = fragment_id
        self.name = name
        self.description = description
        self.parameters = parameters or []

    def model_dump(self, mode: str = "json") -> dict:
        return {
            "template_id": self.template_id,
            "fragment_id": self.fragment_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class StyleListItem:
    """Style item for discovery."""

    def __init__(self, style_id: str, name: str, description: str):
        self.style_id = style_id
        self.name = name
        self.description = description

    def model_dump(self, mode: str = "json") -> dict:
        return {
            "style_id": self.style_id,
            "name": self.name,
            "description": self.description,
        }


class ErrorResponse:
    """Error response structure."""

    def __init__(
        self, error_code: str, message: str, recovery_strategy: str, details: Optional[dict] = None
    ):
        self.error_code = error_code
        self.message = message
        self.recovery_strategy = recovery_strategy
        self.details = details

    def model_dump(self, mode: str = "json") -> dict:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "recovery_strategy": self.recovery_strategy,
            "details": self.details,
        }


class GetProxyDocumentInput:
    """Input for retrieving a proxied document."""

    def __init__(self, proxy_guid: str, token: Optional[str] = None):
        self.proxy_guid = proxy_guid
        self.token = token

    @classmethod
    def model_validate(cls, data: dict):
        return cls(**data)


class GetProxyDocumentOutput:
    """Output from retrieving a proxied document."""

    def __init__(
        self, proxy_guid: str, format: OutputFormat, content: str, message: str, group: str = None
    ):
        self.proxy_guid = proxy_guid
        self.format = format
        self.content = content
        self.message = message
        self.group = group  # Stored group ownership for access control verification

    def model_dump(self, mode: str = "json") -> dict:
        result = {
            "proxy_guid": self.proxy_guid,
            "format": self.format.value if isinstance(self.format, OutputFormat) else self.format,
            "content": self.content,
            "message": self.message,
        }
        if self.group is not None:
            result["group"] = self.group
        return result
