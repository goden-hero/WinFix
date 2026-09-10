from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from app.schemas.session import WinFixSession


class SessionStore:
    """Small local store. Session JSON keeps MVP migrations intentionally simple."""

    def __init__(self, database_path: str | None = None) -> None:
        default = Path(__file__).resolve().parents[2] / "data" / "winfix.db"
        self.path = Path(database_path or os.getenv("WINFIX_DATABASE_PATH", str(default)))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def save(self, session: WinFixSession) -> WinFixSession:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO sessions(session_id, payload) VALUES (?, ?)",
                (session.session_id, session.model_dump_json()),
            )
        return session

    def get(self, session_id: str) -> WinFixSession | None:
        with self._connect() as connection:
            row = connection.execute("SELECT payload FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        return WinFixSession.model_validate_json(row[0]) if row else None
