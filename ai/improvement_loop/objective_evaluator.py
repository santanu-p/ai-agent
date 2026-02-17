from __future__ import annotations

from dataclasses import dataclass

from .telemetry_collector import MetricsSnapshot


@dataclass(slots=True)
class ObjectiveWeights:
    retention: float = 0.35
    quest_completion: float = 0.25
    deaths: float = 0.20
    economy_stability: float = 0.20


@dataclass(slots=True)
class FitnessScore:
    total: float
    components: dict[str, float]


class ObjectiveEvaluator:
    """Evaluates how healthy the game state is given a metrics snapshot."""

    def __init__(self, weights: ObjectiveWeights | None = None) -> None:
        self.weights = weights or ObjectiveWeights()

    def evaluate(self, snapshot: MetricsSnapshot) -> FitnessScore:
        retention = (snapshot.retention_d1 + snapshot.retention_d7) / 2
        quest_completion = snapshot.quest_completion_rate

        total_deaths = max(sum(snapshot.death_causes.values()), 1)
        top_death_ratio = max(snapshot.death_causes.values(), default=0) / total_deaths
        death_health = max(0.0, 1.0 - top_death_ratio)

        inflation_delta = abs(1.0 - snapshot.economy_inflation_index)
        economy_stability = max(0.0, 1.0 - inflation_delta)

        components = {
            "retention": retention,
            "quest_completion": quest_completion,
            "deaths": death_health,
            "economy_stability": economy_stability,
        }

        total = (
            components["retention"] * self.weights.retention
            + components["quest_completion"] * self.weights.quest_completion
            + components["deaths"] * self.weights.deaths
            + components["economy_stability"] * self.weights.economy_stability
        )

        return FitnessScore(total=round(total, 4), components=components)
