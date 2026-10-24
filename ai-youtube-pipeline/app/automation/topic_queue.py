"""Queue-based topic selection that preserves order and skips duplicates."""

from __future__ import annotations

from typing import Iterable, List, Optional

from app.automation.automation_manager import AutomationManager


class TopicQueue:
    """Manage an ordered list of candidate topics while skipping duplicates."""

    def __init__(self, history_manager: Optional[AutomationManager] = None) -> None:
        self.history_manager = history_manager or AutomationManager()
        self._pending: List[str] = []
        self._used_topics: set[str] = set()

    def add_topics(self, topics: Iterable[str]) -> None:
        """Append new candidates to the queue while removing empties and duplicates."""
        for raw_topic in topics:
            topic = str(raw_topic).strip()
            if not topic:
                continue
            normalized = topic.lower()
            if normalized in self._used_topics:
                continue
            if normalized in {item.lower() for item in self._pending}:
                continue
            self._pending.append(topic)

    def next_topic(self) -> str:
        """Return the next available topic in order, or raise when none remain."""
        index = 0
        while index < len(self._pending):
            topic = self._pending[index]
            normalized = topic.lower()

            if normalized in self._used_topics:
                del self._pending[index]
                continue
            if self.history_manager.is_duplicate_topic(topic):
                del self._pending[index]
                continue

            del self._pending[index]
            self._used_topics.add(normalized)
            return topic

        raise ValueError("No topics available in the queue")

    def remaining(self) -> List[str]:
        """Return the current queue contents without mutating state."""
        return list(self._pending)
