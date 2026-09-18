"""Simple persisted job history for future automation features."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.utils.persistence import exclusive_lock, write_json_atomic
from app.utils.database import SQLiteStore


class JobHistory:
    """Store and query job history for duplicate detection and retry decisions."""

    def __init__(self, history_path: Optional[Path | str] = None, database_path: Optional[Path | str] = None) -> None:
        self.database = SQLiteStore(database_path) if database_path else None
        if self.database:
            return
        self.history_path = Path(history_path) if history_path else Path("data/job_history.json")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_path.exists():
            write_json_atomic(self.history_path, [])

    def _load(self) -> List[Dict[str, Any]]:
        if self.database:
            with self.database.connect() as connection:
                return [dict(row) for row in connection.execute(
                    "SELECT job_id, topic, status, attempts, format FROM job_history ORDER BY rowid"
                )]
        try:
            return json.loads(self.history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def record(
        self,
        job_id: str,
        topic: str,
        status: str,
        attempts: int = 0,
        video_format: str = "LONG_FORM",
    ) -> Dict[str, Any]:
        """Append a job history record."""
        item = {
            "job_id": job_id,
            "topic": topic,
            "status": status,
            "attempts": attempts,
            "format": video_format,
        }
        if self.database:
            with self.database.connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO job_history(job_id, topic, status, attempts, format, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (job_id, topic, status, attempts, video_format, datetime.now(timezone.utc).isoformat()),
                )
                connection.execute("COMMIT")
            return item
        with exclusive_lock(self.history_path):
            items = self._load()
            items.append(item)
            write_json_atomic(self.history_path, items)
        return item

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Return all job records."""
        return self._load()

    def replace(self, items: List[Dict[str, Any]]) -> None:
        """Atomically replace history records."""
        if self.database:
            with self.database.connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("DELETE FROM job_history")
                connection.executemany(
                    "INSERT INTO job_history(job_id, topic, status, attempts, format, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
                    [(item.get("job_id", ""), item.get("topic", ""), item.get("status", ""),
                      int(item.get("attempts", 0)), item.get("format", "LONG_FORM"),
                      datetime.now(timezone.utc).isoformat()) for item in items],
                )
                connection.execute("COMMIT")
            return
        with exclusive_lock(self.history_path):
            write_json_atomic(self.history_path, items)

    def find_by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Return job records matching the given topic, case-insensitive."""
        normalized = topic.strip().lower()
        return [
            item for item in self._load()
            if str(item.get("topic", "")).strip().lower() == normalized
        ]
