"""Output models for MCP server tools."""

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import OutputFormat


class PingOutput(BaseModel):
    """Output for ping."""

    model_config = ConfigDict(extra="ignore")

    status: str
    timestamp: str
    message: str


class TemplateListItem(BaseModel):
    """Template item for discovery responses."""

    template_id: str
    name: str
    description: str
    group: str  # Mandatory - comes from loaded template metadata


class TemplateDetailsOutput(BaseModel):
    """Template details including parameters."""

    model_config = ConfigDict(extra="ignore")

    template_id: str
    name: str
    description: str
    group: str  # Mandatory - comes from template metadata
    global_parameters: List[Any] = Field(default_factory=list)  # Can be ParameterSchema or dict


class FragmentListItem(BaseModel):
    """Fragment item in template discovery."""

    model_config = ConfigDict(extra="ignore")

    fragment_id: str
    name: str
    description: str
    parameter_count: int


class FragmentDetailsOutput(BaseModel):
    """Detailed information about a fragment."""

    model_config = ConfigDict(extra="ignore")

    template_id: str
    fragment_id: str
    name: str
    description: str
    parameters: List[Any] = Field(default_factory=list)  # Can be ParameterSchema or dict


class StyleListItem(BaseModel):
    """Style item for discovery."""

    model_config = ConfigDict(extra="ignore")

    style_id: str
    name: str
    description: str


class CreateSessionOutput(BaseModel):
    """Output from creating a new document session."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    alias: str
    template_id: str
    created_at: str


class SetGlobalParametersOutput(BaseModel):
    """Output from setting global parameters."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    message: str


class SessionFragmentInfo(BaseModel):
    """Information about a fragment instance in a session."""

    model_config = ConfigDict(extra="ignore")

    fragment_instance_guid: str
    fragment_id: str
    fragment_name: str
    position: int
    parameters: dict = Field(default_factory=dict)


class AddFragmentOutput(BaseModel):
    """Output from adding a fragment to a session."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    fragment_instance_guid: str
    fragment_id: str
    position: int
    message: str


class RemoveFragmentOutput(BaseModel):
    """Output from removing a fragment from a session."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    fragment_instance_guid: str
    message: str


class ListSessionFragmentsOutput(BaseModel):
    """Output from listing fragments in a session."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    fragment_count: int
    fragments: List[Any] = Field(default_factory=list)


class AbortSessionOutput(BaseModel):
    """Output from aborting a session."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    message: str


class GetDocumentOutput(BaseModel):
    """Output from document rendering.

    When proxy=true, returns proxy_guid and download_url instead of content.
    When proxy=false, returns full content for direct use.
    """

    model_config = ConfigDict(extra="ignore")

    session_id: str
    format: OutputFormat
    style_id: str
    content: str
    message: str
    proxy_guid: Optional[str] = None
    download_url: Optional[str] = None  # Full URL to download proxy document from web server


class GetProxyDocumentOutput(BaseModel):
    """Output from retrieving a proxied document."""

    model_config = ConfigDict(extra="ignore")

    proxy_guid: str
    format: OutputFormat
    content: str
    message: str
    group: Optional[str] = None  # Stored group ownership for access control verification


class SessionStatusOutput(BaseModel):
    """Output from get_session_status showing current session state."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    template_id: str
    group: str
    has_global_parameters: bool
    fragment_count: int
    is_ready_to_render: bool
    created_at: str
    updated_at: str
    message: str


class SessionSummary(BaseModel):
    """Summary information for a session."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    alias: Optional[str] = None  # Friendly name for the session
    template_id: str
    group: str
    fragment_count: int
    has_global_parameters: bool
    created_at: str
    updated_at: str


class ListActiveSessionsOutput(BaseModel):
    """Output from list_active_sessions showing all available sessions."""

    model_config = ConfigDict(extra="ignore")

    session_count: int
    sessions: List[SessionSummary] = Field(default_factory=list)


class ValidationErrorDetail(BaseModel):
    """Detailed validation error with context."""

    model_config = ConfigDict(extra="ignore")

    parameter: str
    error: str
    expected_type: Optional[str] = None
    received_type: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    example: Optional[Any] = None


class ValidateParametersOutput(BaseModel):
    """Output from validate_parameters showing validation results."""

    model_config = ConfigDict(extra="ignore")

    is_valid: bool
    parameter_type: str  # 'global' or 'fragment'
    template_id: str
    fragment_id: Optional[str] = None
    errors: List[ValidationErrorDetail] = Field(default_factory=list)
    message: str = ""


class HelpOutput(BaseModel):
    """Output from help tool with comprehensive workflow documentation."""

    model_config = ConfigDict(extra="ignore")

    service_name: str
    version: str
    workflow_overview: str
    guid_persistence: str
    common_pitfalls: List[str]
    example_workflows: List[dict]
    tool_sequence: List[dict]
