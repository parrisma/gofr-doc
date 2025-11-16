"""Persistence layer for document sessions."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

from app.config import get_default_sessions_dir
from app.logger import Logger
from app.validation.document_models import DocumentSession


class SessionStore:
    """File-based storage for document sessions."""

    def __init__(self, base_dir: Optional[str] = None, logger: Optional[Logger] = None) -> None:
        self.base_dir = Path(base_dir or get_default_sessions_dir())
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def save_session(self, session: DocumentSession) -> None:
        """Persist a document session to disk."""

        await asyncio.to_thread(self._save_session_sync, session)

    async def load_session(self, session_id: str) -> Optional[DocumentSession]:
        """Load a session from disk."""

        return await asyncio.to_thread(self._load_session_sync, session_id)

    async def delete_session(self, session_id: str) -> None:
        """Remove a session file if it exists."""

        await asyncio.to_thread(self._delete_session_sync, session_id)

    async def list_sessions(self) -> list[str]:
        """List all persisted session IDs."""

        return await asyncio.to_thread(self._list_sessions_sync)

    # ------------------------------------------------------------------
    # Internal helpers (synchronous)
    # ------------------------------------------------------------------

    def _session_path(self, session_id: str) -> Path:
        return self.base_dir / f"{session_id}.json"

    def _save_session_sync(self, session: DocumentSession) -> None:
        data = {
            "session_id": session.session_id,
            "template_id": session.template_id,
            "group": session.group,
            "global_parameters": session.global_parameters,
            "fragments": [
                {
                    "fragment_id": f.fragment_id,
                    "fragment_instance_guid": f.fragment_instance_guid,
                    "parameters": f.parameters,
                    "created_at": f.created_at,
                }
                for f in session.fragments
            ],
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }
        path = self._session_path(session.session_id)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        if self.logger:
            self.logger.debug("Session persisted", session_id=session.session_id, path=str(path))

    def _load_session_sync(self, session_id: str) -> Optional[DocumentSession]:
        path = self._session_path(session_id)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            session = DocumentSession(**data)
            if self.logger:
                self.logger.debug("Session loaded", session_id=session_id, path=str(path))
            return session
        except Exception as exc:  # pragma: no cover - logged upstream
            if self.logger:
                self.logger.error(
                    "Failed to load session", session_id=session_id, path=str(path), error=str(exc)
                )
            raise

    def _delete_session_sync(self, session_id: str) -> None:
        path = self._session_path(session_id)
        if path.exists():
            path.unlink(missing_ok=True)
            if self.logger:
                self.logger.info("Session deleted", session_id=session_id, path=str(path))

    def _list_sessions_sync(self) -> list[str]:
        return [path.stem for path in self.base_dir.glob("*.json") if path.is_file()]


__all__ = ["SessionStore"]
