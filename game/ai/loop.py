"""Autonomous AI tuning loop: Observe -> Evaluate -> ProposePatch -> Validate -> Deploy."""

from __future__ import annotations

from dataclasses import dataclass, field

from .metrics import KPIReadings
from .patch_format import AIPatch
from .validator import PatchValidator, RuntimeStats, SimulationResult


@dataclass
class PatchVersion:
    version: int
    patch: AIPatch
    kpis: KPIReadings
    status: str


@dataclass
class DeploymentLedger:
    versions: list[PatchVersion] = field(default_factory=list)

    @property
    def active(self) -> PatchVersion | None:
        for version in reversed(self.versions):
            if version.status == "active":
                return version
        return None

    def add_active(self, patch: AIPatch, kpis: KPIReadings) -> PatchVersion:
        next_version = (self.versions[-1].version + 1) if self.versions else 1
        if self.active:
            self.active.status = "superseded"
        entry = PatchVersion(version=next_version, patch=patch, kpis=kpis, status="active")
        self.versions.append(entry)
        return entry

    def rollback(self, reason: str) -> PatchVersion | None:
        current = self.active
        if not current:
            return None
        current.status = f"rolled_back:{reason}"

        for version in reversed(self.versions):
            if version.status == "superseded":
                version.status = "active"
                return version
        return None


class AdaptiveAILoop:
    def __init__(self, validator: PatchValidator, ledger: DeploymentLedger | None = None) -> None:
        self.validator = validator
        self.ledger = ledger or DeploymentLedger()

    def run_cycle(
        self,
        observed_baseline: KPIReadings,
        proposed_patch: AIPatch,
        evaluated_candidate: KPIReadings,
        simulation_results: list[SimulationResult],
        runtime_stats: RuntimeStats,
    ) -> tuple[bool, str]:
        # Observe
        baseline = observed_baseline

        # Evaluate
        candidate = evaluated_candidate

        # ProposePatch
        patch = proposed_patch

        # Validate
        report = self.validator.validate(
            patch=patch,
            baseline_kpis=baseline,
            candidate_kpis=candidate,
            sim_results=simulation_results,
            runtime_stats=runtime_stats,
        )
        if not report.passed:
            return False, "Validation failed: " + "; ".join(report.reasons)

        # Deploy
        self.ledger.add_active(patch=patch, kpis=candidate)
        return True, f"Patch {patch.patch_id} deployed"

    def monitor_and_rollback(
        self,
        post_deploy_kpis: KPIReadings,
        max_allowed_regression_ratio: float | None = None,
    ) -> tuple[bool, str]:
        active = self.ledger.active
        if not active:
            return False, "No active deployment"

        threshold = (
            max_allowed_regression_ratio
            if max_allowed_regression_ratio is not None
            else self.validator.max_allowed_regression_ratio
        )
        regression = post_deploy_kpis.regression_ratio(active.kpis)
        if regression > threshold:
            restored = self.ledger.rollback(reason=f"kpi_regression:{regression:.2%}")
            if restored:
                return True, f"Auto-reverted to version {restored.version}"
            return True, "Deployment rolled back but no prior version available"

        return False, "No rollback required"
