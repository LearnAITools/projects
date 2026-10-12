"""Notification hooks for automation job lifecycle events."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from app.utils.logger import get_logger
from app.utils.persistence import exclusive_lock, write_json_atomic

logger = get_logger(__name__)


class Notifier(Protocol):
    """Interface for notifying about workflow events."""

    def notify(
        self,
        job_id: str,
        topic: str,
        status: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send a completion or failure notification."""


class ConsoleNotifier:
    """Simple notifier that logs the event to the app logger."""

    def notify(
        self,
        job_id: str,
        topic: str,
        status: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        logger.info(
            "Automation notification: job_id=%s topic=%s status=%s message=%s payload=%s",
            job_id,
            topic,
            status,
            message,
            payload,
        )


class DurableNotifier:
    """Persist notification delivery state while delegating actual delivery."""

    def __init__(
        self,
        delegate: Notifier,
        notification_path: Path | str = "data/notifications.json",
        max_attempts: int = 3,
        base_delay_seconds: int = 2,
    ) -> None:
        if max_attempts <= 0 or base_delay_seconds <= 0:
            raise ValueError("notification retry settings must be greater than zero")
        self.delegate = delegate
        self.notification_path = Path(notification_path)
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.notification_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.notification_path.exists():
            write_json_atomic(self.notification_path, [])

    def _load(self) -> list[Dict[str, Any]]:
        try:
            payload = json.loads(self.notification_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return payload if isinstance(payload, list) else []

    def _save(self, records: list[Dict[str, Any]]) -> None:
        write_json_atomic(self.notification_path, records)

    @staticmethod
    def _notification_id(job_id: str, status: str) -> str:
        value = f"{job_id}:{status}".encode("utf-8")
        return hashlib.sha256(value).hexdigest()

    def notify(
        self,
        job_id: str,
        topic: str,
        status: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Deliver once immediately, persisting failure state for later retry."""
        notification_id = self._notification_id(job_id, status)
        with exclusive_lock(self.notification_path):
            records = self._load()
            record = next(
                (item for item in records if item.get("notification_id") == notification_id),
                None,
            )
            if record is None:
                record = {
                    "notification_id": notification_id,
                    "job_id": job_id,
                    "topic": topic,
                    "status": status,
                    "message": message,
                    "payload": payload or {},
                    "attempts": 0,
                    "delivery_status": "PENDING",
                }
                records.append(record)
            if record.get("delivery_status") == "DELIVERED":
                return
            next_attempt_at = record.get("next_attempt_at")
            if next_attempt_at and datetime.fromisoformat(next_attempt_at) > datetime.now(timezone.utc):
                return
            record["attempts"] = int(record.get("attempts", 0)) + 1
            try:
                self.delegate.notify(job_id, topic, status, message, payload)
            except Exception as exc:
                record["delivery_status"] = "FAILED"
                record["last_error"] = str(exc)
                if record["attempts"] < self.max_attempts:
                    record["next_attempt_at"] = (
                        datetime.now(timezone.utc)
                        + timedelta(seconds=self.base_delay_seconds * 2 ** (record["attempts"] - 1))
                    ).isoformat()
                else:
                    record["next_attempt_at"] = None
                self._save(records)
                logger.error("Notification delivery failed for %s: %s", job_id, exc)
                return
            record["delivery_status"] = "DELIVERED"
            record["delivered_at"] = datetime.now(timezone.utc).isoformat()
            record["next_attempt_at"] = None
            self._save(records)

    def list_notifications(self) -> list[Dict[str, Any]]:
        """Return persisted notification delivery records."""
        return self._load()

    def retry_pending(self, now: Optional[datetime] = None) -> int:
        """Retry failed notifications whose backoff has elapsed."""
        reference = now or datetime.now(timezone.utc)
        pending = [
            item for item in self._load()
            if item.get("delivery_status") == "FAILED"
            and item.get("attempts", 0) < self.max_attempts
            and item.get("next_attempt_at")
            and datetime.fromisoformat(item["next_attempt_at"]) <= reference
        ]
        for item in pending:
            with exclusive_lock(self.notification_path):
                records = self._load()
                for record in records:
                    if record.get("notification_id") == item.get("notification_id"):
                        record["next_attempt_at"] = None
                        self._save(records)
                        break
            self.notify(
                item["job_id"], item["topic"], item["status"], item["message"], item.get("payload")
            )
        return len(pending)
