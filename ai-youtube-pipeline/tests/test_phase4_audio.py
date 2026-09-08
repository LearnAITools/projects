from pathlib import Path

from app.audio.narration_generator import NarrationGenerator
from app.audio.voice_provider import LocalPlaceholderVoiceProvider
from app.content.models import GeneratedContent, Scene, YouTubeMetadata


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


def test_local_placeholder_voice_provider_creates_wav(tmp_path):
    provider = LocalPlaceholderVoiceProvider()
    output = tmp_path / "scene_001.wav"

    path = provider.generate_audio("Hello world", output)

    assert path == output
    assert output.exists()
    assert output.suffix.lower() == ".wav"


def test_narration_generator_reuses_existing_audio(tmp_path):
    content = make_content()
    generator = NarrationGenerator(
        provider=LocalPlaceholderVoiceProvider(),
        base_dir=str(tmp_path),
    )

    first_run = generator.generate(job_id="job_audio_001", content=content)
    second_run = generator.generate(job_id="job_audio_001", content=content, force=False)

    assert len(first_run) == 2
    assert first_run[0].exists()
    assert second_run == first_run


def test_narration_generator_uses_deterministic_names(tmp_path):
    content = make_content()
    generator = NarrationGenerator(
        provider=LocalPlaceholderVoiceProvider(),
        base_dir=str(tmp_path),
    )

    files = generator.generate(job_id="job_audio_002", content=content)

    assert [p.name for p in files] == ["scene_001.wav", "scene_002.wav"]
