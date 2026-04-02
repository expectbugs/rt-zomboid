"""SQLite storage for conversations, events, and relationship scores."""

import sqlite3
import time
from pathlib import Path


class MemoryStore:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_schema(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    personality TEXT NOT NULL,
                    player TEXT NOT NULL,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_conv_lookup
                    ON conversations(personality, player, timestamp DESC);

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    game_state_json TEXT,
                    timestamp REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                    ON events(timestamp DESC);

                CREATE TABLE IF NOT EXISTS relationship_scores (
                    player TEXT PRIMARY KEY,
                    score INTEGER NOT NULL DEFAULT 0,
                    last_updated REAL NOT NULL
                );
            """)

    def log_conversation(self, personality: str, player: str,
                         role: str, message: str):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO conversations (personality, player, role, message, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (personality, player, role, message, time.time()),
            )

    def get_recent_conversations(self, personality: str, player: str,
                                 limit: int = 10) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT role, message, timestamp FROM conversations "
                "WHERE personality = ? AND player = ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (personality, player, limit),
            ).fetchall()
        # Return in chronological order
        return [dict(r) for r in reversed(rows)]

    def get_recent_unified(self, player: str, limit: int = 10) -> list[dict]:
        """Get recent messages from ALL personalities for a player."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT personality, role, message, timestamp FROM conversations "
                "WHERE player = ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (player, limit),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def log_event(self, event_type: str, description: str,
                  game_state_json: str | None = None):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO events (event_type, description, game_state_json, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (event_type, description, game_state_json, time.time()),
            )

    def get_relationship_score(self, player: str) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT score FROM relationship_scores WHERE player = ?",
                (player,),
            ).fetchone()
        return row["score"] if row else 0

    def set_relationship_score(self, player: str, score: int):
        score = max(-100, min(100, score))
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO relationship_scores (player, score, last_updated) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(player) DO UPDATE SET score = ?, last_updated = ?",
                (player, score, time.time(), score, time.time()),
            )
