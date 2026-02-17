from __future__ import annotations

from collections import defaultdict, deque


class TieredMemory:
    def __init__(self) -> None:
        self._episodic: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=100))
        self._session: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=200))
        self._semantic: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=500))

    def append_episodic(self, run_id: str, entry: str) -> None:
        self._episodic[run_id].append(entry)

    def append_session(self, goal_id: str, entry: str) -> None:
        self._session[goal_id].append(entry)

    def append_semantic(self, topic: str, entry: str) -> None:
        self._semantic[topic].append(entry)

    def read_episodic(self, run_id: str) -> list[str]:
        return list(self._episodic.get(run_id, []))

    def read_session(self, goal_id: str) -> list[str]:
        return list(self._session.get(goal_id, []))

    def read_semantic(self, topic: str) -> list[str]:
        return list(self._semantic.get(topic, []))

    def snapshot(self, run_id: str, goal_id: str, topic: str) -> dict[str, list[str]]:
        return {
            "episodic": self.read_episodic(run_id),
            "session": self.read_session(goal_id),
            "semantic": self.read_semantic(topic),
        }

