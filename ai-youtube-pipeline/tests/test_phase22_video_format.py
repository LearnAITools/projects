import json

from app.automation.scheduler import AutomationScheduler
from app.content.models import GeneratedContent, VideoFormat
from app.content.prompts import build_topic_prompt
from app.main import build_parser
from app.pipeline.orchestrator import PipelineOrchestrator


def test_short_format_has_vertical_rendering_requirements():
    assert VideoFormat.SHORT.rendering_requirements == {
        "aspect_ratio": "9:16",
        "resolution": "1080x1920",
    }


def test_generated_content_defaults_to_long_form():
    content = GeneratedContent.model_validate({
        "topic": "AI tools",
        "title": "AI Tools",
        "hook": "A useful hook.",
        "script": "A useful script.",
        "scenes": [{
            "scene_number": 1,
            "narration": "A scene.",
            "visual_description": "A developer at work.",
            "duration_seconds": 5,
        }],
        "youtube": {
            "title": "AI Tools",
            "description": "A useful description.",
        },
    })

    assert content.format is VideoFormat.LONG_FORM


def test_short_format_persists_in_schedule_and_job_state(tmp_path):
    schedule_path = tmp_path / "schedule.json"
    scheduler = AutomationScheduler(schedule_file=schedule_path)
    scheduled = scheduler.schedule(
        topic="Short AI tips",
        interval_seconds=60,
        run_immediately=True,
        format=VideoFormat.SHORT,
    )

    reloaded = AutomationScheduler(schedule_file=schedule_path)
    assert reloaded.jobs[0].format is VideoFormat.SHORT

    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path / "jobs"))
    job = orchestrator.create_job(
        topic=scheduled.topic,
        job_id=scheduled.job_id,
        format=scheduled.format,
    )
    state = json.loads((tmp_path / "jobs" / job.job_id / "job_state.json").read_text())
    assert state["format"] == "SHORT"
    assert orchestrator.load_job(job.job_id).format is VideoFormat.SHORT


def test_cli_accepts_short_format():
    args = build_parser().parse_args(["--run-once", "--topic", "AI tips", "--format", "short"])

    assert args.format == "short"


def test_short_format_is_in_prompt():
    prompt = build_topic_prompt("AI tips", video_format=VideoFormat.SHORT)

    assert "SHORT" in prompt
    assert "1080x1920" in prompt
    assert '"format": "SHORT"' in prompt
