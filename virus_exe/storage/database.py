import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any

from virus_exe.missions.model import MissionResult


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    duration REAL NOT NULL,
                    total_infection REAL NOT NULL,
                    detection REAL NOT NULL,
                    moves INTEGER NOT NULL,
                    scans INTEGER NOT NULL,
                    infections INTEGER NOT NULL,
                    hides INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def save_session(self, mission_id: str, result: MissionResult) -> int:
        values = asdict(result)
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO sessions (
                    mission_id, status, reason, score, duration, total_infection,
                    detection, moves, scans, infections, hides
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mission_id,
                    values["status"],
                    values["reason"],
                    values["score"],
                    values["duration"],
                    values["total_infection"],
                    values["detection"],
                    values["moves"],
                    values["scans"],
                    values["infections"],
                    values["hides"],
                ),
            )
            return int(cursor.lastrowid)

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return dict(row) if row else None

    def leaderboard(self, limit: int = 20) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 100))
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, mission_id, status, score, duration, total_infection,
                       detection, moves, scans, infections, hides, created_at
                FROM sessions
                WHERE status = 'WON'
                ORDER BY score DESC, duration ASC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def summary(self) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS sessions,
                       COALESCE(MAX(score), 0) AS best_score,
                       COALESCE(AVG(detection), 0) AS average_detection
                FROM sessions
                """
            ).fetchone()
        return dict(row)
