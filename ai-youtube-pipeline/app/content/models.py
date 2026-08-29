"""Pydantic models for structured video content."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Scene(BaseModel):
    """Represents a single video scene."""

    model_config = ConfigDict(extra="forbid")

    scene_number: int = Field(..., ge=1)
    narration: str
    visual_description: str
    duration_seconds: int = Field(..., gt=0)

    @field_validator("narration", "visual_description")
    @classmethod
    def non_empty_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Field must not be empty")
        return value.strip()


class YouTubeMetadata(BaseModel):
    """Metadata required for YouTube publishing."""

    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    tags: List[str] = Field(default_factory=list)

    @field_validator("title", "description")
    @classmethod
    def non_empty_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Field must not be empty")
        return value.strip()


class GeneratedContent(BaseModel):
    """Validated output from the Claude content generator."""

    model_config = ConfigDict(extra="forbid")

    topic: str
    title: str
    hook: str
    script: str
    scenes: List[Scene]
    youtube: YouTubeMetadata

    @field_validator("topic", "title", "hook", "script")
    @classmethod
    def non_empty_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Field must not be empty")
        return value.strip()

    @field_validator("scenes")
    @classmethod
    def scenes_must_not_be_empty(cls, value: List[Scene]) -> List[Scene]:
        if not value:
            raise ValueError("At least one scene is required")
        return value
