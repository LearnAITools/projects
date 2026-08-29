from pathlib import Path

from app.content.models import GeneratedContent, Scene, YouTubeMetadata
from app.images.image_generator import ImageGenerator
from app.images.image_provider import LocalPlaceholderImageProvider


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


def test_local_placeholder_provider_creates_png(tmp_path):
    provider = LocalPlaceholderImageProvider()
    output = tmp_path / "scene_001.png"

    path = provider.generate_image("Developer using AI assistant", output)

    assert path == output
    assert output.exists()
    assert output.suffix.lower() == ".png"


def test_image_generator_reuses_existing_files(tmp_path):
    content = make_content()
    generator = ImageGenerator(
        provider=LocalPlaceholderImageProvider(),
        base_dir=str(tmp_path),
    )

    first_run = generator.generate(job_id="job_001", content=content)
    second_run = generator.generate(job_id="job_001", content=content, force=False)

    assert len(first_run) == 2
    assert first_run[0].exists()
    assert second_run == first_run


def test_image_generator_generates_deterministic_names(tmp_path):
    content = make_content()
    generator = ImageGenerator(
        provider=LocalPlaceholderImageProvider(),
        base_dir=str(tmp_path),
    )

    files = generator.generate(job_id="job_002", content=content)

    assert [p.name for p in files] == ["scene_001.png", "scene_002.png"]
