from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class MetricsSnapshot:
    """Normalized gameplay telemetry used by the improvement loop."""

    captured_at: str
    retention_d1: float
    retention_d7: float
    quest_completion_rate: float
    death_causes: dict[str, int] = field(default_factory=dict)
    economy_inflation_index: float = 1.0
    avg_session_minutes: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "captured_at": self.captured_at,
            "retention_d1": self.retention_d1,
            "retention_d7": self.retention_d7,
            "quest_completion_rate": self.quest_completion_rate,
            "death_causes": self.death_causes,
            "economy_inflation_index": self.economy_inflation_index,
            "avg_session_minutes": self.avg_session_minutes,
            "metadata": self.metadata,
        }


class TelemetryCollector:
    """Collects core gameplay metrics and emits a snapshot per iteration."""

    def collect(
        self,
        *,
        retention_d1: float,
        retention_d7: float,
        quest_completion_rate: float,
        death_causes: dict[str, int],
        economy_inflation_index: float,
        avg_session_minutes: float,
        metadata: dict[str, Any] | None = None,
    ) -> MetricsSnapshot:
        return MetricsSnapshot(
            captured_at=datetime.now(tz=timezone.utc).isoformat(),
            retention_d1=retention_d1,
            retention_d7=retention_d7,
            quest_completion_rate=quest_completion_rate,
            death_causes=death_causes,
            economy_inflation_index=economy_inflation_index,
            avg_session_minutes=avg_session_minutes,
            metadata=metadata or {},
        )
