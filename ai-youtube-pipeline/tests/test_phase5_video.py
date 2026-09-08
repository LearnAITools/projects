from pathlib import Path

from app.content.models import GeneratedContent, Scene, YouTubeMetadata
from app.video.video_builder import VideoBuilder


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


def test_video_builder_creates_final_mp4(tmp_path):
    content = make_content()
    job_dir = tmp_path / "job_video_001"
    job_dir.mkdir()

    image_paths = [
        job_dir / "images" / "scene_001.png",
        job_dir / "images" / "scene_002.png",
    ]
    audio_paths = [
        job_dir / "audio" / "scene_001.wav",
        job_dir / "audio" / "scene_002.wav",
    ]

    for path in image_paths + audio_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"placeholder")

    builder = VideoBuilder(base_dir=str(tmp_path))
    output = builder.build(job_id="job_video_001", content=content, image_paths=image_paths, audio_paths=audio_paths)

    assert output.exists()
    assert output.name == "final.mp4"
    assert output.stat().st_size > 0


def test_video_builder_reuses_existing_video(tmp_path):
    content = make_content()
    builder = VideoBuilder(base_dir=str(tmp_path))

    output = builder.build(job_id="job_video_002", content=content, image_paths=[], audio_paths=[])
    second_output = builder.build(job_id="job_video_002", content=content, image_paths=[], audio_paths=[], force=False)

    assert output == second_output
    assert output.exists()
