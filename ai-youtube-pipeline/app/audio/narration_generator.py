"""Narration orchestration for video scenes."""

from __future__ import annotations

from pathlib import Path
from typing import List

from app.audio.voice_provider import HttpVoiceProvider, LocalPlaceholderVoiceProvider, VoiceProvider
from app.content.models import GeneratedContent
from app.utils.file_manager import FileManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NarrationGenerator:
    """Generate per-scene voice audio, reusing existing output when available."""

    def __init__(
        self,
        provider: VoiceProvider | None = None,
        base_dir: str | None = None,
        file_manager: FileManager | None = None,
    ) -> None:
        self.file_manager = file_manager or FileManager()
        self.base_dir = Path(base_dir) if base_dir else Path(self.file_manager.settings.data_dir)
        if provider is not None:
            self.provider = provider
        elif self.file_manager.settings.voice_provider == "http":
            self.provider = HttpVoiceProvider(
                endpoint=self.file_manager.settings.voice_api_url or "",
                api_key=self.file_manager.settings.voice_api_key or "",
                timeout_seconds=self.file_manager.settings.voice_timeout_seconds,
                max_retries=self.file_manager.settings.voice_max_retries,
            )
        else:
            self.provider = LocalPlaceholderVoiceProvider()

    def _job_dir(self, job_id: str) -> Path:
        return self.file_manager.get_audio_dir(job_id)

    def generate(
        self,
        job_id: str,
        content: GeneratedContent,
        force: bool = False,
    ) -> List[Path]:
        """Generate narration audio for each scene."""
        job_audio_dir = self._job_dir(job_id)
        generated: List[Path] = []

        for scene in content.scenes:
            filename = f"scene_{scene.scene_number:03d}.wav"
            output_path = job_audio_dir / filename

            if output_path.exists() and not force:
                logger.info("Reusing existing narration audio: %s", output_path)
                generated.append(output_path)
                continue

            logger.info("Generating narration audio for scene %s", scene.scene_number)
            self.provider.generate_audio(scene.narration, output_path)
            generated.append(output_path)

        return generated
