"""Read-only monitoring helpers for persisted pipeline jobs."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class JobMonitor:
    """Inspect persisted job state without mutating pipeline data."""

    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Return valid persisted job states ordered by job ID."""
        jobs: List[Dict[str, Any]] = []
        if not self.data_dir.exists():
            return jobs

        for state_path in sorted(self.data_dir.glob("*/job_state.json")):
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                if isinstance(state, dict) and state.get("job_id"):
                    jobs.append(state)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Skipping unreadable job state %s: %s", state_path, exc)
        return jobs

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Return one job state, or None when it does not exist."""
        if not job_id or Path(job_id).name != job_id:
            return None

        state_path = self.data_dir / job_id / "job_state.json"
        if not state_path.exists():
            return None
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Unable to read job state %s: %s", state_path, exc)
            return None
        return state if isinstance(state, dict) else None

    def summary(self) -> Dict[str, Any]:
        """Return aggregate counts by pipeline status."""
        jobs = self.list_jobs()
        counts = Counter(str(job.get("status", "UNKNOWN")) for job in jobs)
        return {
            "total": len(jobs),
            "by_status": dict(sorted(counts.items())),
        }
