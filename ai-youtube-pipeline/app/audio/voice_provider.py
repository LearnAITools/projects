"""Voice provider abstraction for Phase 4."""

from __future__ import annotations

import base64
import io
from abc import ABC, abstractmethod
from pathlib import Path
import time

import requests
import wave

from app.utils.logger import get_logger

logger = get_logger(__name__)


class VoiceProvider(ABC):
    """Provider interface for generating narration audio."""

    @abstractmethod
    def generate_audio(self, text: str, output_path: Path) -> Path:
        """Generate audio for the provided narration text and save it."""


class HttpVoiceProvider(VoiceProvider):
    """Generate narration through a JSON HTTP endpoint.

    The endpoint receives ``{"text": "..."}`` and returns audio bytes,
    ``{"url": "..."}``, ``{"audio_url": "..."}``, or ``{"audio_base64": "..."}``.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        timeout_seconds: float = 30,
        max_retries: int = 2,
    ) -> None:
        if not endpoint:
            raise ValueError("Voice provider endpoint is required")
        if not api_key:
            raise ValueError("VOICE_API_KEY is required for HTTP voice provider")
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.last_usage: dict = {}

    def _post(self, text: str) -> requests.Response:
        for attempt in range(self.max_retries + 1):
            response = requests.post(
                self.endpoint,
                json={"text": text},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout_seconds,
            )
            if response.status_code not in {429, *range(500, 600)}:
                response.raise_for_status()
                return response
            if attempt < self.max_retries:
                time.sleep(2**attempt)
        response.raise_for_status()
        return response

    def generate_audio(self, text: str, output_path: Path) -> Path:
        """Generate, validate, and save WAV audio returned by the HTTP endpoint."""
        response = self._post(text)
        content_type = response.headers.get("content-type", "")
        audio_bytes = response.content
        if "json" in content_type:
            payload = response.json()
            self.last_usage = payload.get("usage", {})
            if payload.get("audio_base64"):
                audio_bytes = base64.b64decode(payload["audio_base64"])
            else:
                audio_url = payload.get("audio_url") or payload.get("url")
                if not audio_url:
                    raise RuntimeError("Voice provider response did not contain audio data or a URL")
                audio_response = requests.get(audio_url, timeout=self.timeout_seconds)
                audio_response.raise_for_status()
                audio_bytes = audio_response.content

        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
                if wav_file.getnframes() <= 0:
                    raise ValueError("empty audio")
        except Exception as exc:
            raise RuntimeError("Voice provider returned invalid WAV audio") from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_bytes)
        logger.info("Generated provider narration audio: %s", output_path)
        return output_path


class LocalPlaceholderVoiceProvider(VoiceProvider):
    """Simple local placeholder voice provider for development and tests."""

    def generate_audio(self, text: str, output_path: Path) -> Path:
        """Generate a simple WAV tone file as a placeholder for narration audio."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        sample_rate = 22050
        amplitude = 16000
        duration_seconds = max(1, min(3, len(text) // 12 + 1))
        total_samples = int(sample_rate * duration_seconds)

        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            frames = bytearray()
            for i in range(total_samples):
                value = int(amplitude * (0.5 + 0.5 * __import__("math").sin(2 * __import__("math").pi * (i / max(1, sample_rate // 2)))))
                frames.extend(int(value).to_bytes(2, byteorder="little", signed=True))

            wav_file.writeframes(bytes(frames))

        logger.info("Generated placeholder narration audio: %s", output_path)
        return output_path
