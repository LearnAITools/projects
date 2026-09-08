from pathlib import Path
from unittest.mock import MagicMock, patch

from app.youtube.youtube_client import YouTubeClient, YouTubeUploadResult


def test_youtube_client_builds_dry_run_metadata():
    client = YouTubeClient(dry_run=True)
    payload = client.prepare_upload_payload(
        title="Test Video",
        description="A test description",
        tags=["ai", "youtube"],
        category_id="22",
        privacy_status="private",
    )

    assert payload["title"] == "Test Video"
    assert payload["dry_run"] is True
    assert payload["privacy_status"] == "private"


def test_youtube_client_handles_missing_credentials_in_dry_run():
    client = YouTubeClient(dry_run=True, client_id=None, client_secret=None)
    result = client.upload_video(video_path=Path("example.mp4"), title="Test", description="Desc")
    assert result.success is True
    assert result.dry_run is True


def test_youtube_client_rejects_upload_when_not_dry_run_without_credentials():
    client = YouTubeClient(dry_run=False, client_id=None, client_secret=None)
    result = client.upload_video(video_path=Path("example.mp4"), title="Test", description="Desc")
    assert result.success is False
    assert result.dry_run is False
    assert "credentials" in result.message.lower()


def test_youtube_client_performs_resumable_upload(tmp_path):
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"video")

    request = MagicMock()
    request.next_chunk.side_effect = [(None, {"id": "uploaded-123"})]
    service = MagicMock()
    service.videos.return_value.insert.return_value = request
    client = YouTubeClient(
        dry_run=False,
        client_id="client-id",
        client_secret="client-secret",
    )

    with patch.object(client, "_get_authenticated_service", return_value=service):
        result = client.upload_video(
            video_path=video_path,
            title="Test",
            description="Description",
            tags=["ai"],
        )

    assert result.success is True
    assert result.video_id == "uploaded-123"
    assert result.upload_url.endswith("uploaded-123")
    service.videos.return_value.insert.assert_called_once()
