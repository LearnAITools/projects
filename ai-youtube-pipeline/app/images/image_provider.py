"""Image provider abstractions for Phase 3."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ImageProvider(ABC):
    """Provider interface for generating scene images."""

    @abstractmethod
    def generate_image(self, prompt: str, output_path: Path) -> Path:
        """Generate an image for a given prompt and save it to the output path."""


class LocalPlaceholderImageProvider(ImageProvider):
    """Simple local placeholder image provider for development and tests."""

    def generate_image(self, prompt: str, output_path: Path) -> Path:
        """Create a placeholder PNG with the scene prompt rendered on it."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        width, height = 1280, 720
        image = Image.new("RGB", (width, height), color=(24, 32, 50))
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 32)
        except Exception:
            font = ImageFont.load_default()

        wrapped = prompt[:120]
        draw.text((60, 60), wrapped, fill=(255, 255, 255), font=font)
        image.save(output_path, format="PNG")

        logger.info("Generated placeholder image: %s", output_path)
        return output_path
