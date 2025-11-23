"""Common models and enums used across the document generation system."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OutputFormat(str, Enum):
    """Supported output formats for document rendering."""

    HTML = "html"
    PDF = "pdf"
    MARKDOWN = "markdown"
    MD = "markdown"  # Alias


class ErrorResponse(BaseModel):
    """Error response structure."""

    model_config = ConfigDict(extra="ignore")

    error_code: str
    message: str
    recovery_strategy: str
    details: Optional[dict] = None
