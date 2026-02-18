from __future__ import annotations

from typing import Optional


def resolve_session_identifier(identifier: str, group: str, manager) -> Optional[str]:
    """Resolve session identifier (alias or GUID) to session GUID.

    Args:
        identifier: Either a session alias or GUID
        group: Group context for alias resolution
        manager: SessionManager instance

    Returns:
        Session GUID if found, None otherwise
    """
    # Try to resolve as alias first, falls back to treating as GUID
    session_id = manager.resolve_session(group, identifier)
    if session_id:
        return session_id
    # If resolve_session returns None, check if it's a valid GUID that exists
    if manager._is_valid_uuid(identifier):
        return identifier
    return None
