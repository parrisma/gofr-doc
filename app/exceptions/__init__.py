"""Custom exceptions for group-aware registries and rendering pipeline.

All exceptions include detailed error messages designed for LLM processing,
enabling intelligent error recovery and decision-making.
"""
from app.exceptions.base import RegistryError
from app.exceptions.template import TemplateNotFoundError
from app.exceptions.fragment import FragmentNotFoundError
from app.exceptions.group import GroupMismatchError
from app.exceptions.style import StyleNotFoundError
from app.exceptions.invalid_group import InvalidGroupError

__all__ = [
    "RegistryError",
    "TemplateNotFoundError",
    "FragmentNotFoundError",
    "GroupMismatchError",
    "StyleNotFoundError",
    "InvalidGroupError",
]
