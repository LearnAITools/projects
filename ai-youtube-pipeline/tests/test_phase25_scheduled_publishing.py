import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.automation.automation_manager import AutomationManager
from app.automation.full_automation import FullAutomation
from app.automation.scheduler import AutomationScheduler
from app.content.models import GeneratedContent, Scene, VideoFormat, YouTubeMetadata
from app.main import build_parser, main
from app.pipeline.orchestrator import PipelineOrchestrator
from app.youtube.youtube_client import YouTubeClient, YouTubeUploadResult


def make_content() -> GeneratedContent:
    return GeneratedContent(
        topic="AI tools",
        format=VideoFormat.LONG_FORM,
        title="AI Tools",
        hook="A useful hook.",
        script="A useful script.",
        scenes=[Scene(
            scene_number=1,
            narration="A scene.",
            visual_description="A developer at work.",
            duration_seconds=5,
        )],
        youtube=YouTubeMetadata(title="AI Tools", description="Useful AI tools."),
    )


def test_publish_at_requires_timezone_and_is_persisted_as_utc(tmp_path):
    schedule_file = tmp_path / "schedules.json"
    publish_at = datetime.now(timezone.utc) + timedelta(hours=1)
    scheduler = AutomationScheduler(schedule_file=schedule_file)
    job = scheduler.schedule(
        topic="Scheduled AI tools",
        interval_seconds=3600,
        publish_at=publish_at,
    )

    assert job.publish_at == publish_at
    assert AutomationScheduler(schedule_file=schedule_file).jobs[0].publish_at == publish_at

    with pytest.raises(ValueError, match="include a timezone"):
        scheduler.schedule(
            topic="Invalid schedule",
            interval_seconds=3600,
            publish_at=datetime.now() + timedelta(hours=1),
        )


def test_youtube_scheduling_requires_private_future_timezone_aware_time():
    client = YouTubeClient(dry_run=True)
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    payload = client.prepare_upload_payload(
        title="Test",
        description="Description",
        privacy_status="private",
        scheduled_publish_time=future,
    )
    assert payload["scheduled_publish_time"].endswith("Z")

    with pytest.raises(ValueError, match="private"):
        client.prepare_upload_payload(
            title="Test",
            description="Description",
            privacy_status="public",
            scheduled_publish_time=future,
        )


def test_full_automation_passes_publish_at_to_youtube(tmp_path):
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "jobs"))
    manager = AutomationManager(history_path=tmp_path / "history.json")
    youtube_client = MagicMock()
    youtube_client.settings.youtube_category_id = "22"
    youtube_client.settings.youtube_privacy_status = "private"
    youtube_client.upload_video.return_value = YouTubeUploadResult(
        success=True,
        message="ok",
        video_id="video-123",
        upload_url="https://youtu.be/video-123",
        dry_run=True,
    )

    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"video")
    automation = FullAutomation(
        orchestrator=orchestrator,
        history_manager=manager,
        content_gen=MagicMock(),
        image_gen=MagicMock(),
        narration_gen=MagicMock(),
        video_builder=MagicMock(),
        youtube_client=youtube_client,
    )
    automation.automation_pipeline.generator.generate.return_value = make_content()
    automation.image_gen.generate.return_value = []
    automation.narration_gen.generate.return_value = []
    automation.video_builder.build.return_value = video_path
    publish_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    result = automation.run_job({
        "job_id": "scheduled_001",
        "topic": "AI tools",
        "publish_at": publish_at,
    })

    assert result["publish_at"] == publish_at
    assert youtube_client.upload_video.call_args.kwargs["scheduled_publish_time"] == publish_at
    state = json.loads((tmp_path / "jobs" / "scheduled_001" / "job_state.json").read_text())
    assert state["publish_at"] == publish_at


def test_cli_can_create_list_and_cancel_persisted_schedule(tmp_path):
    settings = SimpleNamespace(
        environment="test",
        log_level="INFO",
        dry_run=True,
        data_dir=str(tmp_path),
        get_data_dir=lambda: tmp_path,
    )
    publish_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    with patch("app.main.get_settings", return_value=settings):
        assert main([
            "--schedule-topic", "AI tools", "--publish-at", publish_at,
            "--format", "short",
        ]) == 0
        schedule_file = Path(tmp_path) / "schedules.json"
        saved = json.loads(schedule_file.read_text())
        job_id = saved[0]["job_id"]
        assert saved[0]["format"] == "SHORT"
        assert saved[0]["publish_at"].endswith("Z")
        assert main(["--list-schedules"]) == 0
        assert main(["--cancel-schedule", job_id]) == 0
        assert json.loads(schedule_file.read_text()) == []


def test_cli_parser_accepts_schedule_operations():
    args = build_parser().parse_args([
        "--schedule-topic", "AI tools", "--publish-at", "2026-09-05T12:00:00+00:00",
        "--interval-seconds", "3600",
    ])

    assert args.schedule_topic == "AI tools"
    assert args.interval_seconds == 3600
