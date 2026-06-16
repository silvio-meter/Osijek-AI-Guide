"""
In-memory agent sessions for Phase 3 client-tool pause/resume.

Production can swap this for Redis; TTL keeps memory bounded.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import BaseMessage

SESSION_TTL_SECONDS = 600


@dataclass
class AgentSession:
    session_id: str
    user_id: str
    messages: list[BaseMessage]
    language: str
    user_message: str = ""
    iteration: int = 0
    created_at: float = field(default_factory=time.time)
    pending_client_tools: list[dict] = field(default_factory=list)


class AgentSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, AgentSession] = {}

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [sid for sid, s in self._sessions.items() if now - s.created_at > SESSION_TTL_SECONDS]
        for sid in expired:
            del self._sessions[sid]

    def create(
        self,
        *,
        user_id: str,
        messages: list[BaseMessage],
        language: str,
        user_message: str = "",
    ) -> AgentSession:
        self._purge_expired()
        session_id = str(uuid.uuid4())
        session = AgentSession(
            session_id=session_id,
            user_id=user_id,
            messages=messages,
            language=language,
            user_message=user_message,
        )
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str, user_id: str) -> AgentSession | None:
        self._purge_expired()
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.user_id != user_id:
            return None
        if time.time() - session.created_at > SESSION_TTL_SECONDS:
            del self._sessions[session_id]
            return None
        return session

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


agent_session_store = AgentSessionStore()