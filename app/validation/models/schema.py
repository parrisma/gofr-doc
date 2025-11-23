"""Schema models for templates, fragments, and styles loaded from YAML."""

from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ParameterSchema(BaseModel):
    """Schema for a single parameter in templates or fragments."""

    model_config = ConfigDict(extra="allow")  # Allow extra fields from YAML

    name: str
    type: str  # string, integer, number, boolean, array, object
    description: str
    required: bool = True
    default: Optional[Any] = None
    example: Optional[Any] = None
    group: str = "public"  # Parameters inherit group from parent (template/fragment/style)


class TemplateMetadata(BaseModel):
    """Metadata for a template."""

    model_config = ConfigDict(extra="allow")  # Allow extra fields from YAML

    template_id: str
    group: str  # NEW: Mandatory group field (must match directory location)
    name: str
    description: str
    version: str = "1.0.0"


class FragmentSchema(BaseModel):
    """Schema for a reusable fragment."""

    model_config = ConfigDict(extra="allow")  # Allow extra fields from YAML

    fragment_id: str
    group: str  # NEW: Mandatory group field (must match directory location)
    name: str
    description: str
    parameters: List[ParameterSchema] = Field(default_factory=list)


class TemplateSchema(BaseModel):
    """Complete template schema with metadata and fragments."""

    model_config = ConfigDict(extra="allow")  # Allow extra fields from YAML

    metadata: TemplateMetadata
    global_parameters: List[ParameterSchema] = Field(default_factory=list)
    fragments: List[FragmentSchema] = Field(default_factory=list)


class StyleSchema(BaseModel):
    """Schema for a style asset."""

    model_config = ConfigDict(extra="allow")  # Allow extra fields from YAML

    style_id: str
    group: str  # NEW: Mandatory group field (must match directory location)
    name: str
    description: str
    parameters: List[ParameterSchema] = Field(default_factory=list)
