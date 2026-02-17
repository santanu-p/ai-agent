"""Objective specification for AI-driven live tuning and content changes.

Defines balanced optimization targets across retention, challenge, fairness,
and system performance. This module intentionally encodes trade-offs rather
than maximizing a single business metric.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObjectiveWeights:
    """Relative weights for optimization dimensions.

    Weights should sum to 1.0.
    """

    retention: float
    challenge: float
    fairness: float
    performance: float

    def validate(self) -> None:
        total = self.retention + self.challenge + self.fairness + self.performance
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Objective weights must sum to 1.0, got {total:.6f}")


DEFAULT_OBJECTIVE_WEIGHTS = ObjectiveWeights(
    retention=0.32,
    challenge=0.24,
    fairness=0.28,
    performance=0.16,
)


@dataclass(frozen=True)
class ObjectiveGuardrails:
    """Minimum standards that must hold regardless of weighted score."""

    min_fairness_score: float = 0.85
    max_p95_latency_ms: int = 200
    max_crash_rate_delta_pct: float = 0.10
    max_economy_inflation_delta_pct: float = 0.50


DEFAULT_GUARDRAILS = ObjectiveGuardrails()


def composite_score(
    *,
    retention: float,
    challenge: float,
    fairness: float,
    performance: float,
    weights: ObjectiveWeights = DEFAULT_OBJECTIVE_WEIGHTS,
) -> float:
    """Compute weighted objective score after validating weight consistency."""

    weights.validate()
    return (
        retention * weights.retention
        + challenge * weights.challenge
        + fairness * weights.fairness
        + performance * weights.performance
    )


def guardrails_satisfied(
    *,
    fairness_score: float,
    p95_latency_ms: int,
    crash_rate_delta_pct: float,
    economy_inflation_delta_pct: float,
    guardrails: ObjectiveGuardrails = DEFAULT_GUARDRAILS,
) -> bool:
    """Return True only when hard objective guardrails are satisfied."""

    return all(
        [
            fairness_score >= guardrails.min_fairness_score,
            p95_latency_ms <= guardrails.max_p95_latency_ms,
            crash_rate_delta_pct <= guardrails.max_crash_rate_delta_pct,
            economy_inflation_delta_pct <= guardrails.max_economy_inflation_delta_pct,
        ]
    )
