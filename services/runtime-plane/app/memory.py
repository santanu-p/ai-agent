from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


class TieredMemory:
    def __init__(self) -> None:
        self._episodic: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=100))
        self._session: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=200))
        self._semantic: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=500))

    def _entry(self, event: str, cause: str, effect: str, tags: list[str] | None = None) -> dict[str, Any]:
        return {
            "event": event,
            "cause": cause,
            "effect": effect,
            "tags": tags or [],
        }

    def append_episodic(self, run_id: str, event: str, cause: str, effect: str, tags: list[str] | None = None) -> None:
        self._episodic[run_id].append(self._entry(event=event, cause=cause, effect=effect, tags=tags))

    def append_session(self, goal_id: str, event: str, cause: str, effect: str, tags: list[str] | None = None) -> None:
        self._session[goal_id].append(self._entry(event=event, cause=cause, effect=effect, tags=tags))

    def append_semantic(self, topic: str, event: str, cause: str, effect: str, tags: list[str] | None = None) -> None:
        self._semantic[topic].append(self._entry(event=event, cause=cause, effect=effect, tags=tags))

    def read_episodic(self, run_id: str) -> list[dict[str, Any]]:
        return list(self._episodic.get(run_id, []))

    def read_session(self, goal_id: str) -> list[dict[str, Any]]:
        return list(self._session.get(goal_id, []))

    def read_semantic(self, topic: str) -> list[dict[str, Any]]:
        return list(self._semantic.get(topic, []))

    def snapshot(self, run_id: str, goal_id: str, topic: str) -> dict[str, list[dict[str, Any]]]:
        return {
            "episodic": self.read_episodic(run_id),
            "session": self.read_session(goal_id),
            "semantic": self.read_semantic(topic),
        }
