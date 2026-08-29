"""Application configuration settings."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    dry_run: bool = True

    # File Paths
    data_dir: str = "data"

    # Claude API
    claude_api_key: Optional[str] = None

    # Image Generation
    image_api_key: Optional[str] = None
    image_provider: Optional[str] = None

    # Voice Generation
    voice_api_key: Optional[str] = None
    voice_provider: Optional[str] = None

    # YouTube API
    youtube_client_id: Optional[str] = None
    youtube_client_secret: Optional[str] = None
    youtube_redirect_uri: str = "http://localhost:8080/oauth2callback"

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_data_dir(self, subdir: str = "") -> Path:
        """Get data directory path."""
        path = Path(self.data_dir)
        if subdir:
            path = path / subdir
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_log_level_int(self) -> int:
        """Convert log level string to logging module level."""
        import logging

        return getattr(logging, self.log_level.upper(), logging.INFO)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
