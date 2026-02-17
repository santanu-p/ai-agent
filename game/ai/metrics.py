from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Sequence

from .types import KPIReport, Observation


@dataclass(frozen=True, slots=True)
class KPIThresholds:
    """Target ranges used by validators and rollback logic."""

    min_retention_proxy: float = 0.62
    max_quest_completion_time_minutes: float = 24.0
    min_npc_interaction_quality: float = 0.75


class KPICalculator:
    """Compute measurable KPI values and baseline comparisons."""

    def __init__(self, thresholds: KPIThresholds | None = None) -> None:
        self.thresholds = thresholds or KPIThresholds()

    def evaluate(self, current: Observation, baseline_window: Sequence[Observation]) -> KPIReport:
        if not baseline_window:
            baseline_window = [current]

        return KPIReport(
            retention_proxy=current.retention_proxy,
            quest_completion_time_minutes=current.quest_completion_time_minutes,
            npc_interaction_quality=current.npc_interaction_quality,
            baseline_retention_proxy=mean(x.retention_proxy for x in baseline_window),
            baseline_completion_time_minutes=mean(
                x.quest_completion_time_minutes for x in baseline_window
            ),
            baseline_npc_quality=mean(x.npc_interaction_quality for x in baseline_window),
        )

    def regressed(self, report: KPIReport) -> bool:
        """Regression means any KPI moving in the wrong direction beyond tolerance."""

        retention_drop = report.retention_proxy < report.baseline_retention_proxy * 0.97
        completion_slowdown = (
            report.quest_completion_time_minutes
            > report.baseline_completion_time_minutes * 1.05
        )
        npc_quality_drop = report.npc_interaction_quality < report.baseline_npc_quality * 0.97

        return retention_drop or completion_slowdown or npc_quality_drop

    def below_threshold(self, report: KPIReport) -> bool:
        return (
            report.retention_proxy < self.thresholds.min_retention_proxy
            or report.quest_completion_time_minutes
            > self.thresholds.max_quest_completion_time_minutes
            or report.npc_interaction_quality < self.thresholds.min_npc_interaction_quality
        )
