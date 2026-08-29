import json
from unittest.mock import MagicMock, patch

import pytest

from app.content.content_generator import ContentGenerator, ContentValidationError
from app.content.models import GeneratedContent, Scene, YouTubeMetadata
from app.content.prompts import build_topic_prompt


VALID_CONTENT = {
    "topic": "5 AI tools developers should know",
    "title": "5 AI Tools Every Developer Should Know",
    "hook": "AI is changing how developers ship faster.",
    "script": "This video covers five practical AI tools.",
    "scenes": [
        {
            "scene_number": 1,
            "narration": "First, let's talk about AI coding assistants.",
            "visual_description": "Developer using AI coding assistant on laptop.",
            "duration_seconds": 8,
        },
        {
            "scene_number": 2,
            "narration": "Next, consider automated testing tools.",
            "visual_description": "Dashboard with test coverage and automation.",
            "duration_seconds": 7,
        },
    ],
    "youtube": {
        "title": "5 AI Tools Every Developer Should Know",
        "description": "A practical overview of five AI tools that help developers work faster.",
        "tags": ["ai", "developer tools", "software engineering"],
    },
}


def test_build_topic_prompt_contains_topic():
    prompt = build_topic_prompt("5 AI tools that developers should know")
    assert "5 AI tools that developers should know" in prompt
    assert "JSON" in prompt.upper()


def test_generated_content_model_validates_fields():
    content = GeneratedContent.model_validate(VALID_CONTENT)
    assert content.topic == VALID_CONTENT["topic"]
    assert content.scenes[0].scene_number == 1
    assert content.youtube.title == VALID_CONTENT["youtube"]["title"]


def test_invalid_scene_is_rejected():
    with pytest.raises(ValueError):
        Scene.model_validate({
            "scene_number": 0,
            "narration": "bad",
            "visual_description": "bad",
            "duration_seconds": 0,
        })


def test_content_generator_rejects_malformed_payload():
    generator = ContentGenerator()

    with patch.object(generator.client, "generate_content", return_value={"bad": "response"}):
        with pytest.raises(ContentValidationError):
            generator.generate(topic="test topic")


def test_claude_client_parses_json_from_response():
    payload = {"content": [{"type": "text", "text": json.dumps(VALID_CONTENT)}]}

    parsed = ContentGenerator().client.parse_response(payload)
    assert parsed["title"] == VALID_CONTENT["title"]


def test_claude_client_raises_for_invalid_json_text():
    invalid_payload = {"content": [{"type": "text", "text": "not-json"}]}

    with pytest.raises(ValueError):
        ContentGenerator().client.parse_response(invalid_payload)
