"""SQLite persistence primitives for transactional pipeline records."""

from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1


class SQLiteStore:
    """Own a SQLite database and initialize its versioned schema."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        """Open a connection configured for transactional use."""
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS job_history (
                    job_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    format TEXT NOT NULL DEFAULT 'LONG_FORM',
                    recorded_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_job_history_job_id
                    ON job_history(job_id);
                CREATE INDEX IF NOT EXISTS idx_job_history_topic
                    ON job_history(topic COLLATE NOCASE);
                CREATE TABLE IF NOT EXISTS schedules (
                    job_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    next_run_at TEXT NOT NULL,
                    claim_expires_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_schedules_due
                    ON schedules(next_run_at, claim_expires_at);
                """
            )
            version = connection.execute(
                "SELECT version FROM schema_version LIMIT 1"
            ).fetchone()
            if version is None:
                connection.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
            elif int(version[0]) > SCHEMA_VERSION:
                raise RuntimeError("Database schema is newer than this application")

    def backup(self, destination: Path | str) -> Path:
        """Create a consistent SQLite backup at destination."""
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as source, sqlite3.connect(destination) as target:
            source.backup(target)
        return destination

    def migrate_json(self, history_path: Path | str | None = None, schedule_path: Path | str | None = None) -> dict[str, int]:
        """Import legacy JSON records once without deleting their source files."""
        imported = {"history": 0, "schedules": 0}
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if history_path:
                source = Path(history_path)
                existing = connection.execute("SELECT COUNT(*) FROM job_history").fetchone()[0]
                if source.exists() and existing == 0:
                    records = json.loads(source.read_text(encoding="utf-8"))
                    for record in records if isinstance(records, list) else []:
                        connection.execute(
                            "INSERT INTO job_history(job_id, topic, status, attempts, format, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (record.get("job_id", ""), record.get("topic", ""), record.get("status", ""),
                             int(record.get("attempts", 0)), record.get("format", "LONG_FORM"),
                             datetime.now(timezone.utc).isoformat()),
                        )
                        imported["history"] += 1
            if schedule_path:
                source = Path(schedule_path)
                existing = connection.execute("SELECT COUNT(*) FROM schedules").fetchone()[0]
                if source.exists() and existing == 0:
                    records = json.loads(source.read_text(encoding="utf-8"))
                    for record in records if isinstance(records, list) else []:
                        if not isinstance(record, dict) or "job_id" not in record:
                            continue
                        connection.execute(
                            "INSERT OR IGNORE INTO schedules(job_id, payload, next_run_at, claim_expires_at) VALUES (?, ?, ?, ?)",
                            (record["job_id"], json.dumps(record), record.get("next_run_at", ""), record.get("claim_expires_at")),
                        )
                        imported["schedules"] += 1
            connection.execute("COMMIT")
        return imported

    def prune_history(self, before: datetime) -> int:
        """Delete history records older than before and return the count."""
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM job_history WHERE recorded_at < ?", (before.isoformat(),)
            )
            return cursor.rowcount