from __future__ import annotations

from .models import MetricsSnapshot, ObjectiveScores


class ObjectiveEvaluator:
    """Computes fitness score from key product objectives."""

    def __init__(
        self,
        retention_weight: float = 0.4,
        progression_weight: float = 0.3,
        economy_weight: float = 0.2,
        stability_weight: float = 0.1,
    ) -> None:
        self.retention_weight = retention_weight
        self.progression_weight = progression_weight
        self.economy_weight = economy_weight
        self.stability_weight = stability_weight

    def evaluate(self, metrics: MetricsSnapshot) -> ObjectiveScores:
        retention_score = min(1.0, (metrics.retention_d1 * 0.5 + metrics.retention_d7 * 0.5) / 0.5)
        progression_score = min(1.0, metrics.quest_completion_rate / 0.75)
        economy_score = max(0.0, 1.0 - abs(metrics.economy_inflation_index) / 0.1)

        total_deaths = sum(metrics.top_death_causes.values())
        deaths_per_session = total_deaths / max(metrics.active_sessions, 1)
        stability_score = max(0.0, 1.0 - deaths_per_session / 2.0)

        components = {
            "retention": retention_score,
            "progression": progression_score,
            "economy": economy_score,
            "stability": stability_score,
        }
        overall = (
            retention_score * self.retention_weight
            + progression_score * self.progression_weight
            + economy_score * self.economy_weight
            + stability_score * self.stability_weight
        )
        return ObjectiveScores(overall_fitness=overall, score_components=components)
