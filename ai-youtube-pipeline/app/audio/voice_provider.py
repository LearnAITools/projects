"""Voice provider abstraction for Phase 4."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import wave

from app.utils.logger import get_logger

logger = get_logger(__name__)


class VoiceProvider(ABC):
    """Provider interface for generating narration audio."""

    @abstractmethod
    def generate_audio(self, text: str, output_path: Path) -> Path:
        """Generate audio for the provided narration text and save it."""


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
