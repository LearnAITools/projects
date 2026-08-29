"""Claude API client abstraction for content generation."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping

import requests

from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ClaudeClient:
    """Minimal Claude API client with response parsing and validation hooks."""

    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str | None = None, timeout: int = 30):
        self.settings = get_settings()
        self.api_key = api_key or self.settings.claude_api_key
        self.timeout = timeout

    def generate_content(self, prompt: str) -> Dict[str, Any]:
        """Send a prompt to Claude and return the raw JSON response."""
        if not self.api_key:
            raise ValueError("CLAUDE_API_KEY is not configured")

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}],
        }

        logger.info("Calling Claude content API")
        response = requests.post(
            self.API_URL,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()

        data = response.json()
        logger.info("Claude content API call completed")
        return data

    def parse_response(self, raw_response: Mapping[str, Any]) -> Dict[str, Any]:
        """Extract the JSON payload from a Claude response object."""
        content = raw_response.get("content")
        if not isinstance(content, list) or not content:
            raise ValueError("Claude response did not include content blocks")

        first_block = content[0]
        text = first_block.get("text") if isinstance(first_block, dict) else None
        if not isinstance(text, str):
            raise ValueError("Claude response content block did not include text")

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Claude response was not valid JSON: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ValueError("Claude response JSON root must be an object")

        logger.info("Parsed Claude JSON response successfully")
        return parsed
