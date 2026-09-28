"""YouTube Data API client with dry-run safety and OAuth support."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config.settings import get_settings
from app.utils.logger import get_logger
from app.utils.persistence import write_json_atomic

logger = get_logger(__name__)


@dataclass
class YouTubeUploadResult:
    """Result of a YouTube upload attempt."""

    success: bool
    message: str
    dry_run: bool = False
    video_id: Optional[str] = None
    upload_url: Optional[str] = None


class YouTubeClient:
    """Thin client for preparing upload metadata and safely handling dry-run behavior."""

    def __init__(
        self,
        dry_run: Optional[bool] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> None:
        self.settings = get_settings()
        self.dry_run = self.settings.dry_run if dry_run is None else dry_run
        self.client_id = client_id or self.settings.youtube_client_id
        self.client_secret = client_secret or self.settings.youtube_client_secret
        self.redirect_uri = redirect_uri or self.settings.youtube_redirect_uri
        self.token_file = Path(self.settings.youtube_token_file)
        self._upload_state_path: Optional[Path] = None
        self._upload_idempotency_key: Optional[str] = None

    def set_upload_context(self, state_path: Path, idempotency_key: str) -> None:
        """Configure durable state for the next upload request."""
        self._upload_state_path = state_path
        self._upload_idempotency_key = idempotency_key

    def recover_upload(self, state_path: Path) -> Optional[YouTubeUploadResult]:
        """Return a previously confirmed upload result, if one was persisted."""
        if not state_path.exists():
            return None
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if state.get("status") != "COMPLETED" or not state.get("video_id"):
            return None
        return YouTubeUploadResult(
            success=True,
            message="Recovered previously confirmed YouTube upload.",
            dry_run=bool(state.get("dry_run", False)),
            video_id=state["video_id"],
            upload_url=state.get("upload_url"),
        )

    def _save_upload_state(self, state: Dict[str, Any]) -> None:
        if self._upload_state_path is not None:
            write_json_atomic(self._upload_state_path, state)

    def _get_authenticated_service(self) -> Any:
        """Load, refresh, or obtain OAuth credentials and create a YouTube client."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/youtube.upload"]
        credentials = None
        if self.token_file.exists():
            credentials = Credentials.from_authorized_user_file(str(self.token_file), scopes)

        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        elif not credentials or not credentials.valid:
            if not self.client_id or not self.client_secret:
                raise ValueError("YouTube OAuth client credentials are not configured")
            client_config = {
                "installed": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uris": [self.redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, scopes)
            credentials = flow.run_local_server(port=0)

        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(credentials.to_json(), encoding="utf-8")
        return build("youtube", "v3", credentials=credentials)

    def prepare_upload_payload(
        self,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        category_id: str = "22",
        privacy_status: str = "private",
        scheduled_publish_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a structured payload for the YouTube upload request."""
        scheduled_publish_time = self._validate_scheduling(
            privacy_status, scheduled_publish_time
        )
        payload: Dict[str, Any] = {
            "title": title,
            "description": description,
            "tags": tags or [],
            "category_id": category_id,
            "privacy_status": privacy_status,
            "dry_run": self.dry_run,
        }

        if scheduled_publish_time:
            payload["scheduled_publish_time"] = scheduled_publish_time

        return payload

    @staticmethod
    def _validate_scheduling(
        privacy_status: str, scheduled_publish_time: Optional[str]
    ) -> Optional[str]:
        """Validate and normalize YouTube's scheduled publishing fields."""
        if not scheduled_publish_time:
            return None
        if privacy_status != "private":
            raise ValueError("Scheduled YouTube videos must use privacy_status='private'")
        try:
            publish_at = datetime.fromisoformat(scheduled_publish_time.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("scheduled_publish_time must be a valid ISO-8601 timestamp") from exc
        if publish_at.tzinfo is None:
            raise ValueError("scheduled_publish_time must include a timezone")
        if publish_at <= datetime.now(timezone.utc):
            raise ValueError("scheduled_publish_time must be in the future")
        return publish_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        category_id: str = "22",
        privacy_status: str = "private",
        scheduled_publish_time: Optional[str] = None,
    ) -> YouTubeUploadResult:
        """Upload a video to YouTube or simulate the operation in dry-run mode."""
        try:
            scheduled_publish_time = self._validate_scheduling(
                privacy_status, scheduled_publish_time
            )
        except ValueError as exc:
            return YouTubeUploadResult(success=False, message=str(exc), dry_run=self.dry_run)

        if self.dry_run:
            logger.info("YouTube dry-run enabled; skipping actual upload for %s", video_path)
            result = YouTubeUploadResult(
                success=True,
                message="Dry run completed successfully; no upload performed.",
                dry_run=True,
                video_id="dry-run-video-id",
                upload_url=None,
            )
            self._save_upload_state({
                "status": "COMPLETED",
                "idempotency_key": self._upload_idempotency_key,
                "video_id": result.video_id,
                "upload_url": result.upload_url,
                "dry_run": True,
            })
            return result

        if not self.client_id or not self.client_secret:
            logger.warning("YouTube upload attempted without credentials")
            return YouTubeUploadResult(
                success=False,
                message="YouTube upload requires client credentials; configure YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET.",
                dry_run=False,
            )

        if not video_path.is_file():
            return YouTubeUploadResult(
                success=False,
                message=f"Video file does not exist: {video_path}",
                dry_run=False,
            )

        try:
            from googleapiclient.http import MediaFileUpload

            upload_state = {}
            if self._upload_state_path and self._upload_state_path.exists():
                try:
                    upload_state = json.loads(
                        self._upload_state_path.read_text(encoding="utf-8")
                    )
                except (OSError, json.JSONDecodeError):
                    upload_state = {}
            self._save_upload_state({
                "status": "IN_PROGRESS",
                "idempotency_key": self._upload_idempotency_key,
                "video_path": str(video_path),
                "resumable_uri": upload_state.get("resumable_uri"),
                "dry_run": False,
            })

            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags or [],
                    "categoryId": category_id,
                },
                "status": {"privacyStatus": privacy_status},
            }
            if scheduled_publish_time:
                body["status"]["publishAt"] = scheduled_publish_time

            service = self._get_authenticated_service()
            request = service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True),
            )
            if upload_state.get("resumable_uri"):
                request.resumable_uri = upload_state["resumable_uri"]
            response = None
            while response is None:
                _, response = request.next_chunk()
                self._save_upload_state({
                    "status": "IN_PROGRESS",
                    "idempotency_key": self._upload_idempotency_key,
                    "video_path": str(video_path),
                    "resumable_uri": getattr(request, "resumable_uri", None),
                    "dry_run": False,
                })

            video_id = response.get("id") if isinstance(response, dict) else None
            if not video_id:
                raise RuntimeError("YouTube upload response did not include a video ID")
            result = YouTubeUploadResult(
                success=True,
                message="Video uploaded successfully.",
                video_id=video_id,
                upload_url=f"https://www.youtube.com/watch?v={video_id}",
            )
            self._save_upload_state({
                "status": "COMPLETED",
                "idempotency_key": self._upload_idempotency_key,
                "video_id": result.video_id,
                "upload_url": result.upload_url,
                "dry_run": False,
            })
            return result
        except Exception as exc:
            logger.error("YouTube upload failed: %s", exc)
            self._save_upload_state({
                "status": "IN_PROGRESS",
                "idempotency_key": self._upload_idempotency_key,
                "video_path": str(video_path),
                "resumable_uri": locals().get("request", None)
                and getattr(locals()["request"], "resumable_uri", None),
                "last_error": str(exc),
                "dry_run": False,
            })
            return YouTubeUploadResult(
                success=False,
                message=f"YouTube upload failed: {exc}",
                dry_run=False,
            )
