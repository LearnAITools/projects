"""Quality and moderation checks for generated video content."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from app.content.models import GeneratedContent


DEFAULT_BLOCKED_TERMS = frozenset({
    "child sexual abuse",
    "explicit sexual content",
    "instructions to make a bomb",
    "how to make a bomb",
    "racial slur",
})


@dataclass(frozen=True)
class QualityReport:
    """Result of quality and moderation checks."""

    issues: list[str] = field(default_factory=list)
    moderation_flags: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Whether content passed every configured check."""
        return not self.issues and not self.moderation_flags

    @property
    def errors(self) -> list[str]:
        """Return all blocking findings in display order."""
        return [*self.issues, *self.moderation_flags]


class ContentQualityChecker:
    """Validate structural, length, and metadata quality constraints."""

    def check(self, content: GeneratedContent) -> QualityReport:
        issues: list[str] = []
        if len(content.topic) > 200:
            issues.append("Topic must be 200 characters or fewer")
        if len(content.title) > 120:
            issues.append("Title must be 120 characters or fewer")
        if len(content.script) > 100000:
            issues.append("Script must be 100000 characters or fewer")
        if not 1 <= len(content.scenes) <= 100:
            issues.append("Content must contain between 1 and 100 scenes")
        scene_numbers = [scene.scene_number for scene in content.scenes]
        if scene_numbers != list(range(1, len(scene_numbers) + 1)):
            issues.append("Scene numbers must be consecutive starting at 1")
        if len(content.youtube.description) > 5000:
            issues.append("YouTube description must be 5000 characters or fewer")
        if len(content.youtube.tags) > 30:
            issues.append("YouTube metadata must contain 30 tags or fewer")
        if any(not tag.strip() or len(tag) > 100 for tag in content.youtube.tags):
            issues.append("YouTube tags must be non-empty and 100 characters or fewer")
        return QualityReport(issues=issues)


class ContentModerator:
    """Apply a deterministic baseline moderation policy to generated text."""

    def __init__(self, blocked_terms: Iterable[str] | None = None) -> None:
        self.blocked_terms = tuple(blocked_terms or DEFAULT_BLOCKED_TERMS)

    def check(self, content: GeneratedContent) -> QualityReport:
        text = " ".join(
            [content.topic, content.title, content.hook, content.script,
             content.youtube.title, content.youtube.description,
             *[scene.narration for scene in content.scenes],
             *[scene.visual_description for scene in content.scenes]]
        ).casefold()
        flags = [term for term in self.blocked_terms if term.casefold() in text]
        return QualityReport(moderation_flags=flags)


def check_content_quality(
    content: GeneratedContent,
    checker: ContentQualityChecker | None = None,
    moderator: ContentModerator | None = None,
) -> QualityReport:
    """Run quality and moderation checks and combine their findings."""
    quality = (checker or ContentQualityChecker()).check(content)
    moderation = (moderator or ContentModerator()).check(content)
    return QualityReport(
        issues=quality.issues,
        moderation_flags=moderation.moderation_flags,
    )