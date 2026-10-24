from unittest.mock import MagicMock

import pytest

from app.content.content_generator import ContentGenerator, ContentValidationError
from app.content.models import GeneratedContent, VideoFormat
from app.content.prompts import build_topic_prompt


def make_content(total_duration: int, video_format: VideoFormat) -> dict:
    return {
        "topic": "AI tips",
        "format": video_format.value,
        "title": "AI Tips",
        "hook": "A useful hook.",
        "script": "A concise script.",
        "scenes": [{
            "scene_number": 1,
            "narration": "A scene.",
            "visual_description": "A developer at work.",
            "duration_seconds": total_duration,
        }],
        "youtube": {
            "title": "AI Tips",
            "description": "Useful AI tips.",
        },
    }


def test_short_content_must_be_below_180_seconds():
    with pytest.raises(ValueError, match="below 180 seconds"):
        GeneratedContent.model_validate(make_content(180, VideoFormat.SHORT))


def test_short_content_at_179_seconds_is_valid():
    content = GeneratedContent.model_validate(make_content(179, VideoFormat.SHORT))

    assert content.total_duration_seconds == 179


def test_long_form_is_not_limited_by_short_duration_rule():
    content = GeneratedContent.model_validate(make_content(180, VideoFormat.LONG_FORM))

    assert content.total_duration_seconds == 180


def test_blank_topic_is_rejected_before_client_call():
    client = MagicMock()
    generator = ContentGenerator(client=client)

    with pytest.raises(ContentValidationError, match="non-empty"):
        generator.generate("   ", video_format=VideoFormat.SHORT)

    client.generate_content.assert_not_called()


def test_short_prompt_contains_short_constraints():
    prompt = build_topic_prompt("AI tips", video_format=VideoFormat.SHORT)

    assert "first 2 seconds" in prompt
    assert "3 to 8" in prompt
    assert "under 180 seconds" in prompt
    assert "YouTube Shorts" in prompt


def test_long_form_prompt_uses_long_form_guidance():
    prompt = build_topic_prompt("AI tips", video_format=VideoFormat.LONG_FORM)

    assert "first 10 seconds" in prompt
    assert "long-form video" in prompt
    assert "first 2 seconds" not in prompt
