"""Image generation orchestration for pipeline scenes."""

from __future__ import annotations

from pathlib import Path
from typing import List

from app.content.models import GeneratedContent
from app.images.image_provider import ImageProvider, LocalPlaceholderImageProvider
from app.utils.file_manager import FileManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ImageGenerator:
    """Generate per-scene images with caching, naming, and reuse semantics."""

    def __init__(
        self,
        provider: ImageProvider | None = None,
        base_dir: str | None = None,
        file_manager: FileManager | None = None,
    ) -> None:
        self.provider = provider or LocalPlaceholderImageProvider()
        self.file_manager = file_manager or FileManager()
        self.base_dir = Path(base_dir) if base_dir else Path(self.file_manager.settings.data_dir)

    def _job_dir(self, job_id: str) -> Path:
        return self.file_manager.get_images_dir(job_id)

    def generate(
        self,
        job_id: str,
        content: GeneratedContent,
        force: bool = False,
    ) -> List[Path]:
        """Generate images for every scene, reusing existing ones unless forced."""
        job_images_dir = self._job_dir(job_id)
        generated: List[Path] = []

        for scene in content.scenes:
            filename = f"scene_{scene.scene_number:03d}.png"
            output_path = job_images_dir / filename

            if output_path.exists() and not force:
                logger.info("Reusing existing image: %s", output_path)
                generated.append(output_path)
                continue

            logger.info("Generating image for scene %s", scene.scene_number)
            self.provider.generate_image(scene.visual_description, output_path)
            generated.append(output_path)

        return generated
