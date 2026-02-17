"""Candidate patch generation helpers for self-rebuild workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from typing import Callable, Iterable, Sequence


@dataclass(frozen=True)
class ImprovementGoal:
    id: str
    description: str
    priority: int = 0


@dataclass(frozen=True)
class TelemetrySnapshot:
    metric_name: str
    value: float
    baseline: float | None = None
    notes: str = ""


@dataclass(frozen=True)
class CandidatePatch:
    goal_id: str
    summary: str
    diff: str
    confidence: float
    generated_at: str
    telemetry_digest: str


GeneratorFn = Callable[[ImprovementGoal, Sequence[TelemetrySnapshot]], str]


class PatchGenerator:
    """Generates candidate diffs from goals and telemetry."""

    def __init__(self, generator_fn: GeneratorFn):
        self._generator_fn = generator_fn

    def generate_candidates(
        self,
        goals: Iterable[ImprovementGoal],
        telemetry: Sequence[TelemetrySnapshot],
        max_candidates: int = 5,
    ) -> list[CandidatePatch]:
        ranked_goals = sorted(goals, key=lambda g: g.priority, reverse=True)
        candidates: list[CandidatePatch] = []

        for goal in ranked_goals[:max_candidates]:
            diff = self._generator_fn(goal, telemetry).strip()
            if not diff:
                continue
            candidates.append(
                CandidatePatch(
                    goal_id=goal.id,
                    summary=goal.description,
                    diff=diff,
                    confidence=self._estimate_confidence(goal, telemetry, diff),
                    generated_at=datetime.now(timezone.utc).isoformat(),
                    telemetry_digest=_telemetry_digest(telemetry),
                )
            )

        return sorted(candidates, key=lambda c: c.confidence, reverse=True)

    @staticmethod
    def _estimate_confidence(
        goal: ImprovementGoal,
        telemetry: Sequence[TelemetrySnapshot],
        diff_text: str,
    ) -> float:
        # Deterministic, bounded confidence scoring.
        priority_boost = min(max(goal.priority / 10.0, 0.0), 0.3)
        telemetry_factor = min(len(telemetry) * 0.03, 0.3)
        size_penalty = min(len(diff_text.encode("utf-8")) / 200_000.0, 0.4)
        return round(max(0.05, 0.6 + priority_boost + telemetry_factor - size_penalty), 4)


def _telemetry_digest(telemetry: Sequence[TelemetrySnapshot]) -> str:
    payload = "|".join(
        f"{item.metric_name}:{item.value}:{item.baseline}:{item.notes}" for item in telemetry
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def noop_generator(goal: ImprovementGoal, telemetry: Sequence[TelemetrySnapshot]) -> str:
    """Fallback generator implementation that returns no-op output."""

    _ = telemetry
    return ""
