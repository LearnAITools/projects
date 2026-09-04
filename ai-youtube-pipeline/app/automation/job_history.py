"""Simple persisted job history for future automation features."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class JobHistory:
    """Store and query job history for duplicate detection and retry decisions."""

    def __init__(self, history_path: Optional[Path | str] = None) -> None:
        self.history_path = Path(history_path) if history_path else Path("data/job_history.json")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_path.exists():
            self.history_path.write_text("[]", encoding="utf-8")

    def _load(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def record(self, job_id: str, topic: str, status: str, attempts: int = 0) -> Dict[str, Any]:
        """Append a job history record."""
        items = self._load()
        item = {
            "job_id": job_id,
            "topic": topic,
            "status": status,
            "attempts": attempts,
        }
        items.append(item)
        self.history_path.write_text(json.dumps(items, indent=2), encoding="utf-8")
        return item

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Return all job records."""
        return self._load()

    def find_by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Return job records matching the given topic, case-insensitive."""
        normalized = topic.strip().lower()
        return [
            item for item in self._load()
            if str(item.get("topic", "")).strip().lower() == normalized
        ]
