"""Event collection for AI model improvement loops.

This module captures gameplay telemetry to support downstream dataset
construction, training, and evaluation workflows.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional


@dataclass(frozen=True)
class GameEvent:
    """Structured representation of a gameplay event."""

    event_type: str
    timestamp_ms: int
    match_id: str
    entity_id: str
    payload: Dict[str, Any]
    tags: Dict[str, str] = field(default_factory=dict)


class DataCollector:
    """Writes gameplay events as JSONL for model improvement.

    Expected event families:
      - player_behavior
      - npc_outcome
      - economy_metric
      - death_cause
      - quest_completion
    """

    SUPPORTED_EVENT_TYPES = {
        "player_behavior",
        "npc_outcome",
        "economy_metric",
        "death_cause",
        "quest_completion",
    }

    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def log_event(
        self,
        event_type: str,
        match_id: str,
        entity_id: str,
        payload: Mapping[str, Any],
        *,
        tags: Optional[Mapping[str, str]] = None,
        timestamp_ms: Optional[int] = None,
    ) -> GameEvent:
        """Log a strongly-typed event to JSONL storage."""
        if event_type not in self.SUPPORTED_EVENT_TYPES:
            supported = ", ".join(sorted(self.SUPPORTED_EVENT_TYPES))
            raise ValueError(f"Unsupported event_type={event_type!r}. Supported: {supported}")

        event = GameEvent(
            event_type=event_type,
            timestamp_ms=timestamp_ms if timestamp_ms is not None else int(time.time() * 1000),
            match_id=match_id,
            entity_id=entity_id,
            payload=dict(payload),
            tags=dict(tags or {}),
        )
        self._append_jsonl(asdict(event))
        return event

    def log_batch(self, events: Iterable[GameEvent]) -> int:
        """Log a batch of pre-validated events and return written count."""
        count = 0
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as fh:
                for event in events:
                    if event.event_type not in self.SUPPORTED_EVENT_TYPES:
                        continue
                    fh.write(json.dumps(asdict(event), separators=(",", ":")) + "\n")
                    count += 1
        return count

    def _append_jsonl(self, row: Mapping[str, Any]) -> None:
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(dict(row), separators=(",", ":")) + "\n")
