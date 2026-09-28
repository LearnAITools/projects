import json
from pathlib import Path
from unittest.mock import MagicMock

from app.automation.automation_manager import AutomationManager
from app.automation.full_automation import FullAutomation
from app.content.models import GeneratedContent, Scene, YouTubeMetadata
from app.pipeline.orchestrator import PipelineOrchestrator
from app.youtube.youtube_client import YouTubeUploadResult


CONTENT = GeneratedContent(
    topic="AI tools",
    title="AI Tools for Developers",
    hook="A practical guide to AI tools.",
    script="This video covers useful AI tools.",
    scenes=[
        Scene(
            scene_number=1,
            narration="Use an AI assistant for repetitive coding tasks.",
            visual_description="A developer reviewing code with an AI assistant.",
            duration_seconds=5,
        )
    ],
    youtube=YouTubeMetadata(
        title="AI Tools for Developers",
        description="Useful AI tools for developers.",
        tags=["ai", "development"],
    ),
)


def test_full_automation_persists_youtube_upload_result(tmp_path):
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "jobs"))
    manager = AutomationManager(history_path=tmp_path / "history.json")
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"video")

    video_builder = MagicMock()
    video_builder.build.return_value = video_path
    youtube_client = MagicMock()
    youtube_client.settings.youtube_category_id = "22"
    youtube_client.settings.youtube_privacy_status = "private"
    youtube_client.upload_video.return_value = YouTubeUploadResult(
        success=True,
        message="Video uploaded successfully.",
        video_id="youtube-123",
        upload_url="https://www.youtube.com/watch?v=youtube-123",
    )

    automation = FullAutomation(
        orchestrator=orchestrator,
        history_manager=manager,
        content_gen=MagicMock(),
        image_gen=MagicMock(),
        narration_gen=MagicMock(),
        video_builder=video_builder,
        youtube_client=youtube_client,
    )
    automation.automation_pipeline.generator.generate.return_value = CONTENT

    result = automation.run_job({"job_id": "upload_001", "topic": "AI tools"})
    state = json.loads(
        (tmp_path / "jobs" / "upload_001" / "job_state.json").read_text()
    )

    assert result["status"] == "COMPLETED"
    assert result["youtube_video_id"] == "youtube-123"
    assert state["status"] == "COMPLETED"
    assert state["youtube_video_id"] == "youtube-123"
    assert state["youtube_upload_url"].endswith("youtube-123")
    youtube_client.upload_video.assert_called_once_with(
        video_path=video_path,
        title=CONTENT.youtube.title,
        description=CONTENT.youtube.description,
        tags=CONTENT.youtube.tags,
        category_id="22",
        privacy_status="private",
    )
