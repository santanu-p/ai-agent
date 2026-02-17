from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from .metrics import KPICalculator
from .types import DeploymentRecord, KPIReport, PatchProposal


@dataclass
class PatchDeployer:
    """Deploy policy patches with versioning and automatic rollback."""

    kpi_calculator: KPICalculator = field(default_factory=KPICalculator)
    history: List[DeploymentRecord] = field(default_factory=list)

    def deploy(self, patch: PatchProposal, kpi_report: KPIReport) -> DeploymentRecord:
        version = self.history[-1].version + 1 if self.history else 1
        record = DeploymentRecord(
            version=version,
            patch_id=patch.patch_id,
            deployed_at=datetime.utcnow(),
            kpi_report=kpi_report,
        )
        self.history.append(record)
        return record

    def evaluate_and_maybe_rollback(self, latest_kpi_report: KPIReport) -> Optional[DeploymentRecord]:
        if not self.history:
            return None

        if not (self.kpi_calculator.regressed(latest_kpi_report) or self.kpi_calculator.below_threshold(latest_kpi_report)):
            return None

        latest = self.history[-1]
        latest.reverted = True
        rollback_version = latest.version - 1
        if rollback_version < 1:
            return latest

        # Mark previous stable version as current by duplicating a no-op rollback event.
        rollback_record = DeploymentRecord(
            version=rollback_version,
            patch_id=f"rollback-to-v{rollback_version}",
            deployed_at=datetime.utcnow(),
            kpi_report=latest_kpi_report,
        )
        self.history.append(rollback_record)
        return rollback_record
