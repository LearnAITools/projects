"""Lightweight scheduler for periodic topic generation."""

from __future__ import annotations

import json
import fcntl
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, List, Optional, Tuple
from uuid import uuid4

from app.content.models import VideoFormat
from app.utils.persistence import write_json_atomic
from app.utils.database import SQLiteStore


def _as_naive_utc(value: datetime) -> datetime:
    """Compare persisted and caller timestamps in one representation."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class ScheduledJob:
    """Represents a scheduled automation run."""

    job_id: str
    topic: str
    interval_seconds: int
    next_run_at: datetime
    format: VideoFormat = VideoFormat.LONG_FORM
    publish_at: Optional[datetime] = None
    run_immediately: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    claim_token: Optional[str] = None
    claim_expires_at: Optional[datetime] = None
    paused: bool = False

    def to_dict(self) -> dict:
        """Serialize the schedule entry to JSON-safe data."""
        return {
            "job_id": self.job_id,
            "topic": self.topic,
            "format": self.format.value,
            "publish_at": (
                self.publish_at.isoformat().replace("+00:00", "Z")
                if self.publish_at
                else None
            ),
            "interval_seconds": self.interval_seconds,
            "next_run_at": self.next_run_at.isoformat(),
            "run_immediately": self.run_immediately,
            "created_at": self.created_at.isoformat(),
            "claim_token": self.claim_token,
            "claim_expires_at": (
                self.claim_expires_at.isoformat() if self.claim_expires_at else None
            ),
            "paused": self.paused,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ScheduledJob":
        """Read a schedule entry from persisted JSON."""
        return cls(
            job_id=payload["job_id"],
            topic=payload["topic"],
            format=VideoFormat(payload.get("format", VideoFormat.LONG_FORM.value)),
            publish_at=(
                datetime.fromisoformat(payload["publish_at"].replace("Z", "+00:00"))
                if payload.get("publish_at")
                else None
            ),
            interval_seconds=int(payload["interval_seconds"]),
            next_run_at=datetime.fromisoformat(payload["next_run_at"]),
            run_immediately=bool(payload.get("run_immediately", False)),
            created_at=datetime.fromisoformat(payload.get("created_at", payload["next_run_at"])),
            claim_token=payload.get("claim_token"),
            claim_expires_at=(
                datetime.fromisoformat(payload["claim_expires_at"])
                if payload.get("claim_expires_at")
                else None
            ),
            paused=bool(payload.get("paused", False)),
        )


class AutomationScheduler:
    """Simple scheduler for recurring topic based jobs."""

    def __init__(
        self,
        schedule_file: Optional[Path | str] = None,
        lease_seconds: int = 300,
        database_path: Optional[Path | str] = None,
    ) -> None:
        self.schedule_file = Path(schedule_file) if schedule_file else None
        self.database = SQLiteStore(database_path) if database_path else None
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be greater than zero")
        self.lease_seconds = lease_seconds
        self.jobs: List[ScheduledJob] = []
        self._load()

    @contextmanager
    def _file_lock(self) -> Iterator[None]:
        """Serialize schedule mutations across processes."""
        if self.schedule_file is None:
            yield
            return
        lock_path = self.schedule_file.with_name(f".{self.schedule_file.name}.lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _load(self) -> None:
        """Load persisted jobs if a schedule file exists."""
        if self.database:
            with self.database.connect() as connection:
                self.jobs = [
                    ScheduledJob.from_dict(json.loads(row[0]))
                    for row in connection.execute(
                        "SELECT payload FROM schedules ORDER BY rowid"
                    )
                ]
            return
        if self.schedule_file is None or not self.schedule_file.exists():
            return

        try:
            payload = json.loads(self.schedule_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self.jobs = []
            return

        self.jobs = [ScheduledJob.from_dict(item) for item in payload if isinstance(item, dict)]

    def _save(self) -> None:
        """Persist the in-memory schedule state."""
        if self.database:
            with self.database.connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("DELETE FROM schedules")
                connection.executemany(
                    "INSERT INTO schedules(job_id, payload, next_run_at, claim_expires_at) VALUES (?, ?, ?, ?)",
                    [(job.job_id, json.dumps(job.to_dict()), job.next_run_at.isoformat(),
                      job.claim_expires_at.isoformat() if job.claim_expires_at else None)
                     for job in self.jobs],
                )
                connection.execute("COMMIT")
            return
        if self.schedule_file is None:
            return
        self.schedule_file.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(self.schedule_file, [job.to_dict() for job in self.jobs])

    def schedule(
        self,
        topic: str,
        interval_seconds: int,
        next_run_at: Optional[datetime] = None,
        run_immediately: bool = False,
        format: VideoFormat = VideoFormat.LONG_FORM,
        publish_at: Optional[datetime] = None,
    ) -> ScheduledJob:
        """Register a periodic job and return the scheduled entry."""
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero")
        if publish_at is not None and publish_at.tzinfo is None:
            raise ValueError("publish_at must include a timezone, such as +00:00 or Z")
        if publish_at is not None:
            publish_at = publish_at.astimezone(timezone.utc)

        if next_run_at is None:
            next_run_at = _utc_now() + timedelta(seconds=interval_seconds)
        if run_immediately:
            next_run_at = _utc_now()

        job = ScheduledJob(
            job_id=str(uuid4()),
            topic=topic,
            format=VideoFormat(format),
            publish_at=publish_at,
            interval_seconds=interval_seconds,
            next_run_at=next_run_at,
            run_immediately=run_immediately,
        )
        with self._file_lock():
            self._load()
            self.jobs.append(job)
            self._save()
        return job

    def get_due_jobs(self, now: Optional[datetime] = None) -> List[ScheduledJob]:
        """Return jobs whose next_run_at is due."""
        reference = _as_naive_utc(now or _utc_now())
        if self.database:
            with self.database.connect() as connection:
                rows = connection.execute(
                    "SELECT payload FROM schedules WHERE next_run_at <= ? "
                    "AND (claim_expires_at IS NULL OR claim_expires_at <= ?) "
                    "ORDER BY next_run_at, rowid",
                    (reference.isoformat(), reference.isoformat()),
                ).fetchall()
            return [
                job for job in (ScheduledJob.from_dict(json.loads(row[0])) for row in rows)
                if not job.paused
            ]
        with self._file_lock():
            self._load()
            return [
                job for job in self.jobs
                if _as_naive_utc(job.next_run_at) <= reference
                and (
                    job.claim_expires_at is None
                    or job.claim_expires_at <= reference
                ) and not job.paused
            ]

    def claim_due_job(
        self, now: Optional[datetime] = None
    ) -> Optional[Tuple[ScheduledJob, str]]:
        """Atomically claim the next due job and return it with its lease token."""
        reference = _as_naive_utc(now or _utc_now())
        if self.database:
            with self.database.connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                rows = connection.execute(
                    "SELECT job_id, payload FROM schedules WHERE next_run_at <= ? "
                    "AND (claim_expires_at IS NULL OR claim_expires_at <= ?) "
                    "ORDER BY next_run_at, rowid",
                    (reference.isoformat(), reference.isoformat()),
                ).fetchall()
                row = next(
                    (candidate for candidate in rows
                     if not ScheduledJob.from_dict(json.loads(candidate[1])).paused),
                    None,
                )
                
                if row is None:
                    connection.execute("COMMIT")
                    return None
                job = ScheduledJob.from_dict(json.loads(row[1]))
                if job.paused:
                    connection.execute("COMMIT")
                    return None
                token = str(uuid4())
                job.claim_token = token
                job.claim_expires_at = reference + timedelta(seconds=self.lease_seconds)
                connection.execute(
                    "UPDATE schedules SET payload = ?, claim_expires_at = ? WHERE job_id = ?",
                    (json.dumps(job.to_dict()), job.claim_expires_at.isoformat(), job.job_id),
                )
                connection.execute("COMMIT")
                return job, token
        with self._file_lock():
            self._load()
            for job in self.jobs:
                if _as_naive_utc(job.next_run_at) > reference:
                    continue
                if job.paused:
                    continue
                if (
                    job.claim_expires_at is not None
                    and _as_naive_utc(job.claim_expires_at) > reference
                ):
                    continue
                token = str(uuid4())
                job.claim_token = token
                job.claim_expires_at = reference + timedelta(seconds=self.lease_seconds)
                self._save()
                return job, token
        return None

    def mark_run(self, job_id: str, claim_token: Optional[str] = None) -> None:
        """Advance a scheduled job to the next execution time."""
        with self._file_lock():
            self._load()
            for job in self.jobs:
                if job.job_id != job_id:
                    continue
                if claim_token is not None and job.claim_token != claim_token:
                    raise ValueError(f"Job {job_id} is not owned by this claim")
                job.next_run_at = _utc_now() + timedelta(seconds=job.interval_seconds)
                job.claim_token = None
                job.claim_expires_at = None
                self._save()
                return

    def release_claim(self, job_id: str, claim_token: str) -> None:
        """Release a claim when a job cannot obtain its execution input."""
        with self._file_lock():
            self._load()
            for job in self.jobs:
                if job.job_id != job_id:
                    continue
                if job.claim_token != claim_token:
                    raise ValueError(f"Job {job_id} is not owned by this claim")
                job.claim_token = None
                job.claim_expires_at = None
                self._save()
                return

    def reschedule_retry(self, job_id: str, retry_at: datetime) -> None:
        """Move a claimed schedule to its persisted retry time."""
        with self._file_lock():
            self._load()
            for job in self.jobs:
                if job.job_id == job_id:
                    job.next_run_at = _as_naive_utc(retry_at)
                    job.claim_token = None
                    job.claim_expires_at = None
                    self._save()
                    return

    def cancel(self, job_id: str) -> bool:
        """Remove a scheduled job and return whether it existed."""
        with self._file_lock():
            self._load()
            original_count = len(self.jobs)
            self.jobs = [job for job in self.jobs if job.job_id != job_id]
            if len(self.jobs) == original_count:
                return False
            self._save()
            return True

    def pause(self, job_id: str) -> bool:
        """Pause a schedule without deleting it."""
        with self._file_lock():
            self._load()
            for job in self.jobs:
                if job.job_id == job_id:
                    job.paused = True
                    self._save()
                    return True
        return False

    def resume(self, job_id: str) -> bool:
        """Resume a paused schedule."""
        with self._file_lock():
            self._load()
            for job in self.jobs:
                if job.job_id == job_id:
                    job.paused = False
                    self._save()
                    return True
        return False

    def retry(self, job_id: str) -> bool:
        """Make a scheduled job immediately eligible for another run."""
        with self._file_lock():
            self._load()
            for job in self.jobs:
                if job.job_id == job_id:
                    job.paused = False
                    job.next_run_at = _utc_now()
                    job.claim_token = None
                    job.claim_expires_at = None
                    self._save()
                    return True
        return False

    def list_jobs(self) -> List[ScheduledJob]:
        """Return all persisted or in-memory scheduled jobs."""
        with self._file_lock():
            self._load()
            return list(self.jobs)
