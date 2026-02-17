from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import MetricsSnapshot, utc_now_iso


@dataclass
class SessionEvent:
    session_id: str
    day_retained: int
    quest_completed: bool
    death_cause: str | None
    economy_delta_pct: float


class TelemetryCollector:
    """Aggregates gameplay events into optimization metrics."""

    def collect(self, events: Iterable[SessionEvent]) -> MetricsSnapshot:
        events = list(events)
        active_sessions = len(events)
        if active_sessions == 0:
            return MetricsSnapshot(
                timestamp=utc_now_iso(),
                retention_d1=0.0,
                retention_d7=0.0,
                quest_completion_rate=0.0,
                top_death_causes={},
                economy_inflation_index=0.0,
                active_sessions=0,
            )

        retention_d1 = sum(1 for e in events if e.day_retained >= 1) / active_sessions
        retention_d7 = sum(1 for e in events if e.day_retained >= 7) / active_sessions
        quest_completion_rate = sum(1 for e in events if e.quest_completed) / active_sessions

        death_causes: dict[str, int] = {}
        for event in events:
            if event.death_cause:
                death_causes[event.death_cause] = death_causes.get(event.death_cause, 0) + 1

        top_death_causes = dict(
            sorted(death_causes.items(), key=lambda kv: kv[1], reverse=True)[:5]
        )
        economy_inflation_index = sum(e.economy_delta_pct for e in events) / active_sessions

        return MetricsSnapshot(
            timestamp=utc_now_iso(),
            retention_d1=retention_d1,
            retention_d7=retention_d7,
            quest_completion_rate=quest_completion_rate,
            top_death_causes=top_death_causes,
            economy_inflation_index=economy_inflation_index,
            active_sessions=active_sessions,
        )
