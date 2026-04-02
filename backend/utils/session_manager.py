"""
Session Manager - Persistent session storage & resumption
==========================================================
Inspired by claw-code session_store.py, adapted for trading bot.

Provides:
- Session persistence to disk (JSON)
- Session resumption with full context
- Automatic cleanup of stale sessions
- Token usage tracking per session
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class SessionMetadata:
    """Immutable session metadata"""

    session_id: str
    user_id: int
    trading_mode: str
    created_at: float
    last_active: float
    message_count: int
    input_tokens: int
    output_tokens: int


@dataclass
class StoredSession:
    """Mutable session data for storage"""

    session_id: str
    user_id: int
    trading_mode: str
    messages: list[dict] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    context: dict = field(default_factory=dict)

    def add_message(self, role: str, content: str, tokens: int = 0) -> None:
        self.messages.append(
            {
                "role": role,
                "content": content,
                "timestamp": time.time(),
            }
        )
        self.last_active = time.time()
        if role == "user":
            self.input_tokens += tokens
        else:
            self.output_tokens += tokens

    def compact_messages(self, keep_last: int = 50) -> None:
        if len(self.messages) > keep_last:
            self.messages[:] = self.messages[-keep_last:]

    @property
    def metadata(self) -> SessionMetadata:
        return SessionMetadata(
            session_id=self.session_id,
            user_id=self.user_id,
            trading_mode=self.trading_mode,
            created_at=self.created_at,
            last_active=self.last_active,
            message_count=len(self.messages),
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        )


class SessionManager:
    """Manages persistent session storage and retrieval"""

    def __init__(self, session_dir: str | Path | None = None):
        self.session_dir = Path(
            session_dir or os.environ.get("SESSION_DIR", ".trading_sessions")
        )
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._active_sessions: dict[str, StoredSession] = {}

    def create_session(
        self,
        user_id: int,
        trading_mode: str = "real",
        session_id: str | None = None,
    ) -> StoredSession:
        """Create a new trading session"""
        import uuid

        sid = session_id or uuid.uuid4().hex[:12]
        session = StoredSession(
            session_id=sid,
            user_id=user_id,
            trading_mode=trading_mode,
        )
        self._active_sessions[sid] = session
        return session

    def save_session(self, session: StoredSession) -> Path:
        """Persist session to disk"""
        path = self.session_dir / f"{session.session_id}.json"
        path.write_text(json.dumps(asdict(session), indent=2))
        return path

    def load_session(self, session_id: str) -> Optional[StoredSession]:
        """Load session from disk"""
        path = self.session_dir / f"{session_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        session = StoredSession(
            session_id=data["session_id"],
            user_id=data["user_id"],
            trading_mode=data["trading_mode"],
            messages=data.get("messages", []),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            created_at=data.get("created_at", time.time()),
            last_active=data.get("last_active", time.time()),
            context=data.get("context", {}),
        )
        self._active_sessions[session_id] = session
        return session

    def get_active_session(self, session_id: str) -> Optional[StoredSession]:
        """Get session from memory"""
        return self._active_sessions.get(session_id)

    def list_sessions(self, user_id: int | None = None) -> list[SessionMetadata]:
        """List all sessions, optionally filtered by user"""
        sessions = []
        for path in self.session_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                if user_id is not None and data.get("user_id") != user_id:
                    continue
                sessions.append(
                    SessionMetadata(
                        session_id=data["session_id"],
                        user_id=data["user_id"],
                        trading_mode=data["trading_mode"],
                        created_at=data.get("created_at", 0),
                        last_active=data.get("last_active", 0),
                        message_count=len(data.get("messages", [])),
                        input_tokens=data.get("input_tokens", 0),
                        output_tokens=data.get("output_tokens", 0),
                    )
                )
            except (json.JSONDecodeError, KeyError):
                continue
        return sorted(sessions, key=lambda s: s.last_active, reverse=True)

    def cleanup_stale_sessions(self, max_age_hours: int = 24) -> int:
        """Remove sessions older than max_age_hours"""
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0
        for path in self.session_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                if data.get("last_active", 0) < cutoff:
                    path.unlink()
                    self._active_sessions.pop(data["session_id"], None)
                    removed += 1
            except (json.JSONDecodeError, KeyError):
                path.unlink(missing_ok=True)
                removed += 1
        return removed
