"""FFmpeg-based video builder for composing final scene clips."""

from __future__ import annotations

import math
import subprocess
import json
import wave
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

from app.content.models import GeneratedContent, VideoFormat
from app.utils.file_manager import FileManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VideoBuilder:
    """Build a final MP4 by composing scene images and narration into a sequence."""

    def __init__(self, base_dir: str | None = None, file_manager: FileManager | None = None) -> None:
        self.file_manager = file_manager or FileManager()
        self.base_dir = Path(base_dir) if base_dir else Path(self.file_manager.settings.data_dir)

    def _job_dir(self, job_id: str) -> Path:
        return self.file_manager.get_video_dir(job_id)

    def _ensure_ffmpeg(self) -> None:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError("ffmpeg is not installed or not available on PATH")

    def _render_dimensions(self, content: GeneratedContent) -> tuple[int, int]:
        """Return the target width and height for the selected video format."""
        if content.format is VideoFormat.SHORT:
            return 1080, 1920
        return 1280, 720

    def _validate_output(
        self,
        path: Path,
        width: int,
        height: int,
        require_audio: bool,
    ) -> None:
        """Validate rendered dimensions, duration, and expected audio presence."""
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Rendered video failed validation: {result.stderr.strip()}")

        try:
            metadata = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Rendered video returned invalid ffprobe metadata") from exc

        streams = metadata.get("streams", [])
        video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
        audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
        if not video_streams:
            raise RuntimeError("Rendered video has no video stream")
        video_stream = video_streams[0]
        if (video_stream.get("width"), video_stream.get("height")) != (width, height):
            raise RuntimeError(
                f"Rendered video dimensions are {video_stream.get('width')}x"
                f"{video_stream.get('height')}; expected {width}x{height}"
            )

        duration = float(metadata.get("format", {}).get("duration", 0) or 0)
        if duration <= 0:
            raise RuntimeError("Rendered video has no positive duration")
        if require_audio and not audio_streams:
            raise RuntimeError("Rendered video is missing the narration audio stream")

    def _ensure_valid_image(self, path: Path, label: str) -> None:
        """Ensure the input image is a usable PNG; otherwise replace it with a placeholder."""
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with Image.open(path) as image:
                image.verify()
            return
        except Exception:
            logger.warning("Image at %s is invalid or unreadable; regenerating placeholder image", path)

        image = Image.new("RGB", (1280, 720), color=(24, 32, 50))
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 38)
        except Exception:
            font = ImageFont.load_default()
        draw.text((80, 300), label[:60], fill=(255, 255, 255), font=font)
        image.save(path, format="PNG")

    def _ensure_valid_audio(self, path: Path) -> None:
        """Ensure the audio input is a valid WAV; otherwise replace it with a placeholder tone."""
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with wave.open(str(path), "rb") as wav_file:
                wav_file.getnframes()
            return
        except Exception:
            logger.warning("Audio at %s is invalid or unreadable; regenerating placeholder audio", path)

        sample_rate = 22050
        duration = 1
        amplitude = 12000
        total_samples = int(sample_rate * duration)

        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            frames = bytearray()
            for i in range(total_samples):
                value = int(amplitude * math.sin(2 * math.pi * 220 * (i / sample_rate)))
                frames.extend(int(value).to_bytes(2, byteorder="little", signed=True))
            wav_file.writeframes(bytes(frames))

    def build(
        self,
        job_id: str,
        content: GeneratedContent,
        image_paths: List[Path] | None = None,
        audio_paths: List[Path] | None = None,
        force: bool = False,
    ) -> Path:
        """Build a final MP4 for the job, reusing an existing video unless forced."""
        job_video_dir = self._job_dir(job_id)
        final_path = job_video_dir / "final.mp4"

        if final_path.exists() and not force:
            logger.info("Reusing existing final video: %s", final_path)
            return final_path

        self._ensure_ffmpeg()
        width, height = self._render_dimensions(content)

        if not image_paths:
            image_paths = []
        if not audio_paths:
            audio_paths = []

        for index, image_path in enumerate(image_paths, start=1):
            self._ensure_valid_image(image_path, f"Scene {index}")

        for index, audio_path in enumerate(audio_paths, start=1):
            self._ensure_valid_audio(audio_path)

        if not image_paths and not audio_paths:
            logger.warning("No media inputs provided for job %s; creating empty placeholder video", job_id)
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c=black:s={width}x{height}:d=1",
                    "-pix_fmt",
                    "yuv420p",
                    str(final_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self._validate_output(final_path, width, height, require_audio=False)
            return final_path

        image_args = []
        for idx, image_path in enumerate(image_paths, start=1):
            image_args.extend(["-loop", "1", "-t", str(content.scenes[idx - 1].duration_seconds), "-i", str(image_path)])

        audio_args = []
        for idx, audio_path in enumerate(audio_paths, start=1):
            audio_args.extend(["-i", str(audio_path)])

        filters = []
        if image_paths:
            for idx in range(len(image_paths)):
                filters.append(
                    f"[{idx}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height},format=yuv420p[v{idx}]"
                )
            video_inputs = "".join(f"[v{idx}]" for idx in range(len(image_paths)))
            if len(image_paths) == 1:
                video_inputs = "[v0]"
            filters.append(f"{video_inputs}concat=n={len(image_paths)}:v=1:a=0[outv]")

        cmd = ["ffmpeg", "-y"]
        cmd.extend(image_args)
        cmd.extend(audio_args)

        if filters:
            cmd.extend(["-filter_complex", ";".join(filters)])
            if image_paths:
                cmd.extend(["-map", "[outv]"])
        if audio_paths:
            cmd.extend(["-map", f"{len(image_paths)}:a"])

        cmd.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", str(final_path)])

        subprocess.run(cmd, check=True, capture_output=True, text=True)
        self._validate_output(final_path, width, height, require_audio=bool(audio_paths))
        logger.info("Built final video: %s", final_path)
        return final_path
