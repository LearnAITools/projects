"""Topic selection logic that avoids duplicate topics in the automation flow."""

from __future__ import annotations

from typing import Iterable, List, Optional

from app.automation.automation_manager import AutomationManager


class TopicSelector:
    """Choose a new topic from a list while skipping duplicates already used."""

    def __init__(self, history_manager: Optional[AutomationManager] = None) -> None:
        self.history_manager = history_manager or AutomationManager()

    def pick_topic(self, candidates: Iterable[str]) -> str:
        """Return the first non-duplicate candidate, or raise ValueError if none remain."""
        options: List[str] = []
        for candidate in candidates:
            topic = str(candidate).strip()
            if not topic:
                continue
            if self.history_manager.is_duplicate_topic(topic):
                continue
            options.append(topic)

        if not options:
            raise ValueError("No selectable topics available after deduplication")

        return options[0]
