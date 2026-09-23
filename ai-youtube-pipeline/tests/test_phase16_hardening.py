import json
from pathlib import Path
from unittest.mock import MagicMock

from app.automation.automation_manager import AutomationManager
from app.automation.full_automation import FullAutomation
from app.content.models import GeneratedContent, Scene, YouTubeMetadata
from app.pipeline.orchestrator import PipelineOrchestrator


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


def test_full_automation_passes_stage_outputs_to_video_builder(tmp_path):
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "jobs"))
    manager = AutomationManager(history_path=tmp_path / "history.json")
    image_paths = [tmp_path / "images" / "scene_001.png"]
    audio_paths = [tmp_path / "audio" / "scene_001.wav"]

    image_generator = MagicMock()
    image_generator.generate.return_value = image_paths
    narration_generator = MagicMock()
    narration_generator.generate.return_value = audio_paths
    video_builder = MagicMock()

    automation = FullAutomation(
        orchestrator=orchestrator,
        history_manager=manager,
        content_gen=MagicMock(),
        image_gen=image_generator,
        narration_gen=narration_generator,
        video_builder=video_builder,
    )
    automation.automation_pipeline.generator.generate.return_value = CONTENT

    result = automation.run_job({"job_id": "hardening_001", "topic": "AI tools"})

    assert result["status"] == "COMPLETED"
    video_builder.build.assert_called_once_with(
        "hardening_001",
        CONTENT,
        image_paths=image_paths,
        audio_paths=audio_paths,
    )


def test_full_automation_persists_failure_stage_and_error(tmp_path):
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "jobs"))
    manager = AutomationManager(history_path=tmp_path / "history.json")
    image_generator = MagicMock()
    image_generator.generate.side_effect = RuntimeError("provider unavailable")

    automation = FullAutomation(
        orchestrator=orchestrator,
        history_manager=manager,
        content_gen=MagicMock(),
        image_gen=image_generator,
        narration_gen=MagicMock(),
        video_builder=MagicMock(),
    )
    automation.automation_pipeline.generator.generate.return_value = CONTENT

    result = automation.run_job({"job_id": "hardening_002", "topic": "AI tools"})
    state = json.loads(
        (tmp_path / "jobs" / "hardening_002" / "job_state.json").read_text()
    )

    assert result["status"] == "FAILED"
    assert state["status"] == "FAILED"
    assert state["stage"] == "images"
    assert state["error"] == "provider unavailable"
