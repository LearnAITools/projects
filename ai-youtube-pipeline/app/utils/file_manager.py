"""File management utilities."""

from pathlib import Path
from typing import Optional

from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FileManager:
    """Handles file operations for the pipeline."""

    def __init__(self):
        """Initialize FileManager with settings."""
        self.settings = get_settings()
        self.base_data_dir = Path(self.settings.data_dir)
        self.base_data_dir.mkdir(parents=True, exist_ok=True)

    def get_job_dir(self, job_id: str) -> Path:
        """
        Get or create job directory.

        Args:
            job_id: Unique job identifier

        Returns:
            Path to job directory
        """
        job_dir = self.base_data_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Job directory: {job_dir}")
        return job_dir

    def get_images_dir(self, job_id: str) -> Path:
        """Get or create images directory for job."""
        images_dir = self.get_job_dir(job_id) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        return images_dir

    def get_audio_dir(self, job_id: str) -> Path:
        """Get or create audio directory for job."""
        audio_dir = self.get_job_dir(job_id) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        return audio_dir

    def get_video_dir(self, job_id: str) -> Path:
        """Get or create video directory for job."""
        video_dir = self.get_job_dir(job_id) / "video"
        video_dir.mkdir(parents=True, exist_ok=True)
        return video_dir

    def get_metadata_path(self, job_id: str) -> Path:
        """Get path to job metadata file."""
        return self.get_job_dir(job_id) / "metadata.json"

    def file_exists(self, file_path: Path) -> bool:
        """Check if file exists."""
        exists = file_path.exists()
        if exists:
            logger.debug(f"File exists: {file_path}")
        return exists

    def save_text(self, file_path: Path, content: str) -> None:
        """Save text to file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        logger.debug(f"Saved text file: {file_path}")

    def load_text(self, file_path: Path) -> str:
        """Load text from file."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        content = file_path.read_text(encoding="utf-8")
        logger.debug(f"Loaded text file: {file_path}")
        return content

    def ensure_dir_exists(self, dir_path: Path) -> Path:
        """Ensure directory exists, create if needed."""
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
