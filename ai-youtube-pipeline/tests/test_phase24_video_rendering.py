import pytest

from app.content.models import GeneratedContent, Scene, VideoFormat, YouTubeMetadata
from app.video.video_builder import VideoBuilder


def make_short_content() -> GeneratedContent:
    return GeneratedContent(
        topic="AI tips",
        format=VideoFormat.SHORT,
        title="AI Tips",
        hook="A useful hook.",
        script="A concise script.",
        scenes=[Scene(
            scene_number=1,
            narration="A scene.",
            visual_description="A developer at work.",
            duration_seconds=5,
        )],
        youtube=YouTubeMetadata(
            title="AI Tips",
            description="Useful AI tips.",
        ),
    )


def test_short_video_is_rendered_as_vertical_mp4(tmp_path):
    job_dir = tmp_path / "short_job"
    image_path = job_dir / "images" / "scene_001.png"
    audio_path = job_dir / "audio" / "scene_001.wav"
    image_path.parent.mkdir(parents=True)
    audio_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"invalid image; builder should replace it")
    audio_path.write_bytes(b"invalid audio; builder should replace it")

    output = VideoBuilder(base_dir=str(tmp_path)).build(
        job_id="short_job",
        content=make_short_content(),
        image_paths=[image_path],
        audio_paths=[audio_path],
    )

    assert output.exists()
    assert output.stat().st_size > 0


def test_video_builder_reports_missing_ffmpeg(tmp_path):
    builder = VideoBuilder(base_dir=str(tmp_path))
    builder._ensure_ffmpeg = lambda: (_ for _ in ()).throw(
        RuntimeError("ffmpeg is not installed or not available on PATH")
    )

    with pytest.raises(RuntimeError, match="ffmpeg is not installed"):
        builder.build(
            "short_job",
            make_short_content(),
            image_paths=[],
            audio_paths=[],
            force=True,
        )
