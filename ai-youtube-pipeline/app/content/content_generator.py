"""Content generation orchestration for the AI YouTube pipeline."""

from __future__ import annotations

from typing import Any, Dict

from app.content.claude_client import ClaudeClient
from app.content.models import GeneratedContent
from app.content.prompts import build_topic_prompt
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ContentValidationError(ValueError):
    """Raised when Claude output cannot be validated into a usable content model."""


class ContentGenerator:
    """Generate structured video content from a topic using Claude."""

    def __init__(self, client: ClaudeClient | None = None):
        self.client = client or ClaudeClient()

    def generate(self, topic: str) -> GeneratedContent:
        """Generate and validate a complete video content specification."""
        prompt = build_topic_prompt(topic)
        logger.info("Generating video content for topic: %s", topic)

        try:
            raw_response = self.client.generate_content(prompt)
            parsed = self.client.parse_response(raw_response)
            content = GeneratedContent.model_validate(parsed)
        except ValueError as exc:
            raise ContentValidationError(f"Claude response failed validation: {exc}") from exc

        logger.info("Content validation succeeded for topic: %s", topic)
        return content
