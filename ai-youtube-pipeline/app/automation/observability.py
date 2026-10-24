"""Structured execution events, aggregate metrics, and operational alerts."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from app.utils.persistence import exclusive_lock, write_json_atomic


class Observability:
    """Persist structured events and evaluate common pipeline failure signals."""

    def __init__(self, data_dir: Path | str = "data") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.data_dir / "events.jsonl"
        self.metrics_path = self.data_dir / "metrics.json"

    def record_event(
        self,
        event: str,
        job_id: Optional[str] = None,
        stage: Optional[str] = None,
        status: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        correlation_id: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Persist one structured event and update aggregate counters."""
        event_id = correlation_id or str(uuid4())
        payload: Dict[str, Any] = {
            "event": event,
            "event_id": str(uuid4()),
            "correlation_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "job_id": job_id,
            "stage": stage,
            "status": status,
        }
        if duration_seconds is not None:
            payload["duration_seconds"] = round(duration_seconds, 6)
        if fields:
            payload.update(fields)
        try:
            with exclusive_lock(self.events_path):
                with self.events_path.open("a", encoding="utf-8") as events_file:
                    events_file.write(json.dumps(payload) + "\n")
                metrics = self._load_metrics()
                metrics["events"] = int(metrics.get("events", 0)) + 1
                metrics[f"event_{event}"] = int(metrics.get(f"event_{event}", 0)) + 1
                if stage and duration_seconds is not None:
                    metrics.setdefault("stage_duration_seconds", {})
                    metrics["stage_duration_seconds"][stage] = round(
                        metrics["stage_duration_seconds"].get(stage, 0) + duration_seconds, 6
                    )
                for metric in ("retry_count", "upload_outcome", "queue_age_seconds"):
                    if metric in payload:
                        key = f"{metric}_{payload[metric]}"
                        metrics[key] = int(metrics.get(key, 0)) + 1
                write_json_atomic(self.metrics_path, metrics)
        except OSError:
            return event_id
        return event_id

    def _load_metrics(self) -> Dict[str, Any]:
        try:
            payload = json.loads(self.metrics_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def metrics(self) -> Dict[str, Any]:
        """Return aggregate metrics."""
        return self._load_metrics()

    def alerts(
        self,
        job_states: list[Dict[str, Any]],
        now: Optional[datetime] = None,
        stuck_after_seconds: int = 3600,
        repeated_failure_attempts: int = 3,
    ) -> list[Dict[str, Any]]:
        """Evaluate stuck, repeated-failure, authentication, and duplicate risks."""
        reference = now or datetime.now(timezone.utc)
        results: list[Dict[str, Any]] = []
        for state in job_states:
            job_id = state.get("job_id")
            if not job_id:
                continue
            updated = state.get("updated_at") or state.get("created_at")
            if updated:
                try:
                    updated_at = datetime.fromisoformat(updated)
                    if updated_at.tzinfo is None:
                        updated_at = updated_at.replace(tzinfo=timezone.utc)
                    age = (reference - updated_at).total_seconds()
                    if age >= stuck_after_seconds and state.get("status") not in {"COMPLETED", "FAILED"}:
                        results.append({"type": "STUCK_JOB", "job_id": job_id, "age_seconds": int(age)})
                except ValueError:
                    pass
            if int(state.get("attempts", 0)) >= repeated_failure_attempts:
                results.append({"type": "REPEATED_FAILURE", "job_id": job_id, "attempts": state["attempts"]})
            error = str(state.get("error") or state.get("last_error") or "").lower()
            if "oauth" in error or "credential" in error or "unauthenticated" in error:
                results.append({"type": "UNAUTHENTICATED", "job_id": job_id})
            if state.get("upload_in_progress") and not state.get("upload_confirmed"):
                results.append({"type": "DUPLICATE_RISK", "job_id": job_id})
        return results