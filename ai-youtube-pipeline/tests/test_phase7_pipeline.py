from pathlib import Path

from app.content.models import GeneratedContent, Scene, YouTubeMetadata
from app.pipeline.orchestrator import PipelineOrchestrator, PipelineJob, JobStatus


def make_content() -> GeneratedContent:
    return GeneratedContent(
        topic="AI tools",
        title="AI Tools Every Developer Should Know",
        hook="AI is changing software delivery.",
        script="This video explains practical AI tools.",
        scenes=[
            Scene(
                scene_number=1,
                narration="First, automate coding tasks.",
                visual_description="A developer using an AI assistant on a laptop.",
                duration_seconds=8,
            ),
            Scene(
                scene_number=2,
                narration="Next, speed up testing.",
                visual_description="A dashboard showing test automation.",
                duration_seconds=7,
            ),
        ],
        youtube=YouTubeMetadata(
            title="AI Tools Every Developer Should Know",
            description="A practical overview of AI tools for developers.",
            tags=["ai", "developer tools", "software engineering"],
        ),
    )


def test_pipeline_job_status_update_and_resume():
    job = PipelineJob(job_id="job_phase7", topic="AI tools")
    assert job.status == JobStatus.CREATED

    job.mark_content_generated()
    job.mark_images_generated()
    job.mark_audio_generated()
    assert job.status == JobStatus.AUDIO_GENERATED


def test_pipeline_orchestrator_creates_and_tracks_job(tmp_path):
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path))
    job = orchestrator.create_job(topic="AI tools")

    assert job.job_id.startswith("job_")
    assert job.status == JobStatus.CREATED
    assert (tmp_path / job.job_id).exists()


def test_pipeline_orchestrator_can_store_and_load_content(tmp_path):
    orchestrator = PipelineOrchestrator(base_dir=str(tmp_path))
    job = orchestrator.create_job(topic="AI tools")
    content = make_content()

    orchestrator.save_content(job.job_id, content)
    loaded = orchestrator.load_content(job.job_id)

    assert loaded.title == content.title
    assert loaded.scenes[0].scene_number == 1
