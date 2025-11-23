"""Session models for document generation."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FragmentInstance(BaseModel):
    """A fragment instance in a document session."""

    model_config = ConfigDict(extra="ignore")

    fragment_id: str
    parameters: dict = Field(default_factory=dict)
    fragment_instance_guid: Optional[str] = None
    created_at: Optional[str] = None


class DocumentSession(BaseModel):
    """Active document session state."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    template_id: str
    created_at: str
    updated_at: str
    group: str  # Mandatory - track group context in session
    global_parameters: dict = Field(default_factory=dict)
    fragments: List[FragmentInstance] = Field(default_factory=list)
