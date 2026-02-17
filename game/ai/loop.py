from __future__ import annotations

from datetime import datetime
from typing import Callable, Sequence

from .deployer import PatchDeployer
from .metrics import KPICalculator
from .types import Observation, PatchProposal
from .validator import PatchValidator


class AutonomousGameAILoop:
    """Observe -> Evaluate -> ProposePatch -> Validate -> Deploy."""

    def __init__(
        self,
        propose_patch: Callable[[Observation], dict],
        validator: PatchValidator | None = None,
        deployer: PatchDeployer | None = None,
        metrics: KPICalculator | None = None,
    ) -> None:
        self.propose_patch = propose_patch
        self.metrics = metrics or KPICalculator()
        self.validator = validator or PatchValidator(kpi_calculator=self.metrics)
        self.deployer = deployer or PatchDeployer(kpi_calculator=self.metrics)

    def run_cycle(self, observation: Observation, baseline_window: Sequence[Observation]) -> dict:
        # 1) Observe
        observed = observation

        # 2) Evaluate
        kpi_report = self.metrics.evaluate(observed, baseline_window)

        # 3) ProposePatch
        proposed_payload = self.propose_patch(observed)
        patch = PatchProposal(
            patch_id=proposed_payload.get("patch_id", f"patch-{observed.run_id}"),
            version_hint=proposed_payload.get("version_hint", "auto"),
            patch_payload=proposed_payload,
            authored_at=datetime.utcnow(),
        )

        # 4) Validate
        validation = self.validator.validate_all(patch, observed, kpi_report)
        if not validation.passed:
            return {
                "status": "validation_failed",
                "reasons": validation.reasons,
                "kpi_report": kpi_report,
            }

        # 5) Deploy
        deployed = self.deployer.deploy(patch, kpi_report)

        # Post-deploy safety: rollback if KPI regresses.
        rollback = self.deployer.evaluate_and_maybe_rollback(kpi_report)
        return {
            "status": "rolled_back" if rollback and rollback.patch_id.startswith("rollback") else "deployed",
            "deployment_version": deployed.version,
            "rollback": rollback.patch_id if rollback else None,
            "kpi_report": kpi_report,
        }
