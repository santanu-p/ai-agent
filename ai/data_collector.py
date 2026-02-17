"""Event collection utilities for the AI improvement subsystem.

This module is responsible for durable, append-only logging of gameplay events
that are later transformed into model training/evaluation datasets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class Event:
    """A normalized gameplay event."""

    event_type: str
    timestamp: str
    session_id: str
    player_id: Optional[str]
    npc_id: Optional[str]
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "event_type": self.event_type,
                "timestamp": self.timestamp,
                "session_id": self.session_id,
                "player_id": self.player_id,
                "npc_id": self.npc_id,
                "payload": self.payload,
            },
            separators=(",", ":"),
            sort_keys=True,
        )


class DataCollector:
    """Thread-safe collector for game telemetry.

    Events are buffered in memory and periodically flushed to a JSONL file.
    """

    SUPPORTED_EVENT_TYPES = {
        "player_behavior",
        "npc_outcome",
        "economy_metric",
        "death_cause",
        "quest_completion",
    }

    def __init__(self, log_path: str | Path, flush_every: int = 50) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.flush_every = max(1, flush_every)
        self._buffer: List[Event] = []
        self._lock = Lock()

    def collect(
        self,
        event_type: str,
        session_id: str,
        payload: Dict[str, Any],
        player_id: Optional[str] = None,
        npc_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> None:
        """Collect and queue a gameplay event."""
        if event_type not in self.SUPPORTED_EVENT_TYPES:
            raise ValueError(f"Unsupported event type: {event_type}")

        event = Event(
            event_type=event_type,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            player_id=player_id,
            npc_id=npc_id,
            payload=payload,
        )

        with self._lock:
            self._buffer.append(event)
            if len(self._buffer) >= self.flush_every:
                self._flush_unlocked()

    def collect_batch(self, events: Iterable[Dict[str, Any]]) -> None:
        """Collect multiple events from dict records."""
        for event in events:
            self.collect(
                event_type=event["event_type"],
                session_id=event["session_id"],
                payload=event.get("payload", {}),
                player_id=event.get("player_id"),
                npc_id=event.get("npc_id"),
                timestamp=event.get("timestamp"),
            )

    def flush(self) -> None:
        with self._lock:
            self._flush_unlocked()

    def _flush_unlocked(self) -> None:
        if not self._buffer:
            return

        with self.log_path.open("a", encoding="utf-8") as handle:
            for event in self._buffer:
                handle.write(event.to_json())
                handle.write("\n")

        self._buffer.clear()


__all__ = ["DataCollector", "Event"]
