"""Validation gates for simulation, performance, and safety."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .metrics import KPIReadings, KPIThresholds
from .patch_format import AIPatch


@dataclass(frozen=True)
class ValidationReport:
    passed: bool
    reasons: list[str]


@dataclass(frozen=True)
class PerformanceBudget:
    max_cpu_ms_per_tick: float = 4.0
    max_memory_mb: float = 128.0


@dataclass(frozen=True)
class SimulationResult:
    scenario: str
    success: bool
    details: str = ""


@dataclass(frozen=True)
class RuntimeStats:
    cpu_ms_per_tick: float
    memory_mb: float


class PatchValidator:
    def __init__(
        self,
        thresholds: KPIThresholds,
        budget: PerformanceBudget | None = None,
        max_allowed_regression_ratio: float = 0.05,
        blocked_targets: Iterable[str] | None = None,
    ) -> None:
        self.thresholds = thresholds
        self.budget = budget or PerformanceBudget()
        self.max_allowed_regression_ratio = max_allowed_regression_ratio
        self.blocked_targets = set(blocked_targets or {"economy.drop_table", "auth.permissions"})

    def validate(
        self,
        patch: AIPatch,
        baseline_kpis: KPIReadings,
        candidate_kpis: KPIReadings,
        sim_results: list[SimulationResult],
        runtime_stats: RuntimeStats,
    ) -> ValidationReport:
        reasons: list[str] = []

        # Format and safety gate.
        try:
            patch.validate()
        except ValueError as err:
            reasons.append(f"patch format check failed: {err}")

        # Simulation regression gate.
        failed_sims = [s for s in sim_results if not s.success]
        if failed_sims:
            reasons.append(
                "simulation regression checks failed: "
                + ", ".join(f"{s.scenario}({s.details})" for s in failed_sims)
            )

        # KPI gate.
        if not candidate_kpis.meets_thresholds(self.thresholds):
            reasons.append("candidate KPI values violate minimum thresholds")
        regression = candidate_kpis.regression_ratio(baseline_kpis)
        if regression > self.max_allowed_regression_ratio:
            reasons.append(
                f"kpi regression ratio {regression:.2%} exceeds cap {self.max_allowed_regression_ratio:.2%}"
            )

        # Performance gate.
        if runtime_stats.cpu_ms_per_tick > self.budget.max_cpu_ms_per_tick:
            reasons.append(
                f"cpu budget exceeded ({runtime_stats.cpu_ms_per_tick}ms > {self.budget.max_cpu_ms_per_tick}ms)"
            )
        if runtime_stats.memory_mb > self.budget.max_memory_mb:
            reasons.append(
                f"memory budget exceeded ({runtime_stats.memory_mb}MB > {self.budget.max_memory_mb}MB)"
            )

        # Exploit/safety gate.
        blocked = [delta.target for delta in patch.deltas if delta.target in self.blocked_targets]
        if blocked:
            reasons.append(f"exploit/safety blocklist hit: {', '.join(sorted(blocked))}")

        return ValidationReport(passed=not reasons, reasons=reasons)
