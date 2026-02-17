from __future__ import annotations

from typing import List, Optional

from .checks import (
    allowed_modification_check,
    canary_telemetry_gate,
    deterministic_replay_gate,
    forbidden_api_check,
    performance_budget_gate,
    prompt_injection_security_gate,
    save_compatibility_gate,
    static_analysis_gate,
)
from .models import EvaluationReport, GateResult, PatchManifest, PatchStatus, PolicyConfig, RevertCallback
from .schema import validate_patch_manifest_schema


class PatchPolicyEngine:
    """Evaluates all required policy gates and auto-reverts on failure."""

    def __init__(self, config: PolicyConfig) -> None:
        self.config = config

    def evaluate(self, manifest: PatchManifest, revert_callback: Optional[RevertCallback] = None) -> EvaluationReport:
        gates: List[GateResult] = [
            validate_patch_manifest_schema(manifest),
            allowed_modification_check(manifest, self.config),
            forbidden_api_check(manifest, self.config),
            static_analysis_gate(manifest),
            deterministic_replay_gate(manifest),
            save_compatibility_gate(manifest, self.config),
            performance_budget_gate(manifest, self.config),
            prompt_injection_security_gate(manifest, self.config),
            canary_telemetry_gate(manifest, self.config),
        ]

        failed = [gate for gate in gates if not gate.passed]
        if failed:
            if revert_callback:
                revert_callback(manifest)
            return EvaluationReport(
                patch_id=manifest.patch_id,
                status=PatchStatus.QUARANTINED,
                gate_results=gates,
                quarantined_reason=failed[0].reason,
            )

        return EvaluationReport(
            patch_id=manifest.patch_id,
            status=PatchStatus.APPROVED,
            gate_results=gates,
            quarantined_reason=None,
        )
