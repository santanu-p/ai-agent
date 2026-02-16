"""KPI definitions and regression helpers for the AI deployment loop."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KPIThresholds:
    """Target and guardrail values used by the deployment validator."""

    min_retention_proxy: float = 0.68
    max_quest_completion_time_minutes: float = 18.0
    min_npc_interaction_quality: float = 0.72


@dataclass(frozen=True)
class KPIReadings:
    """Measured KPI values for one evaluation window."""

    retention_proxy: float
    quest_completion_time_minutes: float
    npc_interaction_quality: float

    def meets_thresholds(self, thresholds: KPIThresholds) -> bool:
        return (
            self.retention_proxy >= thresholds.min_retention_proxy
            and self.quest_completion_time_minutes
            <= thresholds.max_quest_completion_time_minutes
            and self.npc_interaction_quality >= thresholds.min_npc_interaction_quality
        )

    def regression_ratio(self, baseline: "KPIReadings") -> float:
        """Return the worst relative degradation against the baseline.

        Positive numbers indicate a regression; values <= 0 indicate no regression.
        """

        retention_drop = (baseline.retention_proxy - self.retention_proxy) / max(
            baseline.retention_proxy, 1e-6
        )
        quest_slowdown = (
            self.quest_completion_time_minutes - baseline.quest_completion_time_minutes
        ) / max(baseline.quest_completion_time_minutes, 1e-6)
        npc_drop = (
            baseline.npc_interaction_quality - self.npc_interaction_quality
        ) / max(baseline.npc_interaction_quality, 1e-6)
        return max(retention_drop, quest_slowdown, npc_drop)
