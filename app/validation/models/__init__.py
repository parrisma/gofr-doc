"""Document generation validation models - reorganized for better maintainability.

This package contains all Pydantic models used for document generation,
organized by logical grouping:
- schema.py: Template, fragment, and style schemas
- session.py: Document session and fragment instance models
- inputs.py: Input models for MCP tools
- outputs.py: Output models for MCP tools
- common.py: Common models and enums

All models are re-exported here for backward compatibility.
"""

from .common import ErrorResponse, OutputFormat
from .inputs import (
    AbortDocumentSessionInput,
    AddFragmentInput,
    AddImageFragmentInput,
    CreateDocumentSessionInput,
    GetDocumentInput,
    GetFragmentDetailsInput,
    GetProxyDocumentInput,
    GetSessionStatusInput,
    GetTemplateDetailsInput,
    ListActiveSessionsInput,
    ListSessionFragmentsInput,
    ListTemplateFragmentsInput,
    RemoveFragmentInput,
    SetGlobalParametersInput,
    ValidateParametersInput,
)
from .outputs import (
    AbortSessionOutput,
    AddFragmentOutput,
    CreateSessionOutput,
    FragmentDetailsOutput,
    FragmentListItem,
    GetDocumentOutput,
    GetProxyDocumentOutput,
    HelpOutput,
    ListActiveSessionsOutput,
    ListSessionFragmentsOutput,
    PingOutput,
    RemoveFragmentOutput,
    SessionFragmentInfo,
    SessionStatusOutput,
    SessionSummary,
    SetGlobalParametersOutput,
    StyleListItem,
    TemplateDetailsOutput,
    TemplateListItem,
    ValidateParametersOutput,
    ValidationErrorDetail,
)
from .schema import (
    FragmentSchema,
    ParameterSchema,
    StyleSchema,
    TemplateMetadata,
    TemplateSchema,
)
from .session import DocumentSession, FragmentInstance

__all__ = [
    # Common
    "OutputFormat",
    "ErrorResponse",
    # Schema models
    "ParameterSchema",
    "TemplateMetadata",
    "FragmentSchema",
    "TemplateSchema",
    "StyleSchema",
    # Session models
    "FragmentInstance",
    "DocumentSession",
    # Input models
    "GetTemplateDetailsInput",
    "ListTemplateFragmentsInput",
    "GetFragmentDetailsInput",
    "CreateDocumentSessionInput",
    "SetGlobalParametersInput",
    "AddFragmentInput",
    "AddImageFragmentInput",
    "RemoveFragmentInput",
    "ListSessionFragmentsInput",
    "AbortDocumentSessionInput",
    "GetSessionStatusInput",
    "ListActiveSessionsInput",
    "ValidateParametersInput",
    "GetDocumentInput",
    "GetProxyDocumentInput",
    # Output models
    "PingOutput",
    "TemplateListItem",
    "TemplateDetailsOutput",
    "FragmentListItem",
    "FragmentDetailsOutput",
    "StyleListItem",
    "CreateSessionOutput",
    "SetGlobalParametersOutput",
    "SessionFragmentInfo",
    "AddFragmentOutput",
    "RemoveFragmentOutput",
    "ListSessionFragmentsOutput",
    "AbortSessionOutput",
    "GetDocumentOutput",
    "GetProxyDocumentOutput",
    "SessionStatusOutput",
    "SessionSummary",
    "ListActiveSessionsOutput",
    "ValidationErrorDetail",
    "ValidateParametersOutput",
    "HelpOutput",
]
