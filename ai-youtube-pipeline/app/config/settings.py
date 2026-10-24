"""Application configuration settings."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    dry_run: bool = True

    # File Paths
    data_dir: str = "data"
    storage_backend: str = "sqlite"

    # Cost controls (zero disables the corresponding limit)
    monthly_budget_usd: float = Field(default=0, ge=0)
    image_cost_per_unit_usd: float = Field(default=0, ge=0)
    voice_cost_per_unit_usd: float = Field(default=0, ge=0)
    image_quota_units: int = Field(default=0, ge=0)
    voice_quota_units: int = Field(default=0, ge=0)

    # Claude API
    claude_api_key: Optional[str] = None

    # Image Generation
    image_api_key: Optional[str] = None
    image_provider: Optional[str] = None
    image_api_url: Optional[str] = None
    image_timeout_seconds: float = Field(default=30, gt=0)
    image_max_retries: int = Field(default=2, ge=0, le=5)

    # Voice Generation
    voice_api_key: Optional[str] = None
    voice_provider: Optional[str] = None
    voice_api_url: Optional[str] = None
    voice_timeout_seconds: float = Field(default=30, gt=0)
    voice_max_retries: int = Field(default=2, ge=0, le=5)

    # YouTube API
    youtube_client_id: Optional[str] = None
    youtube_client_secret: Optional[str] = None
    youtube_redirect_uri: str = "http://localhost:8080/oauth2callback"
    youtube_token_file: str = "data/youtube_token.json"
    youtube_category_id: str = "22"
    youtube_privacy_status: str = "private"

    @model_validator(mode="after")
    def validate_media_providers(self) -> "Settings":
        for provider_name, api_url, api_key in (
            (self.image_provider, self.image_api_url, self.image_api_key),
            (self.voice_provider, self.voice_api_url, self.voice_api_key),
        ):
            if provider_name and provider_name not in {"local", "http"}:
                raise ValueError(f"Unsupported media provider: {provider_name}")
            if provider_name == "http" and (not api_url or not api_key):
                raise ValueError("HTTP media providers require an API URL and API key")
        return self

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
