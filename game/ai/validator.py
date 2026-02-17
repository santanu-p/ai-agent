from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .metrics import KPICalculator
from .types import KPIReport, Observation, PatchProposal, ValidationResult


class PatchValidator:
    """Validation gates for simulation, performance, and exploit/safety checks."""

    def __init__(self, schema_path: Path | None = None, kpi_calculator: KPICalculator | None = None) -> None:
        self.schema_path = schema_path or Path(__file__).with_name("patch_format.schema.json")
        self.kpi_calculator = kpi_calculator or KPICalculator()
        self.schema = json.loads(self.schema_path.read_text())

    def validate_patch_shape(self, patch: PatchProposal) -> ValidationResult:
        payload = patch.patch_payload

        for required in self.schema["required"]:
            if required not in payload:
                return ValidationResult(False, [f"missing required field: {required}"])

        if payload.get("target") not in self.schema["properties"]["target"]["enum"]:
            return ValidationResult(False, ["unsupported patch target"])

        deltas = payload.get("deltas", [])
        if not isinstance(deltas, list) or not deltas:
            return ValidationResult(False, ["deltas must be a non-empty list"])

        for idx, delta in enumerate(deltas):
            if set(delta.keys()) != {"path", "op", "value"}:
                return ValidationResult(False, [f"delta[{idx}] includes unsupported keys"])
            if not str(delta["path"]).startswith("/"):
                return ValidationResult(False, [f"delta[{idx}] path must be json-pointer-like"])
            if delta["op"] not in {"set", "increase", "decrease"}:
                return ValidationResult(False, [f"delta[{idx}] op invalid"])

        constraints = payload.get("constraints", {})
        if constraints.get("allow_new_tools", False):
            return ValidationResult(False, ["tooling expansion is prohibited in behavior patches"])
        if constraints.get("allow_code_mutation", False):
            return ValidationResult(False, ["code mutation is prohibited in behavior patches"])

        return ValidationResult(True)

    def simulation_regression_checks(self, observation: Observation) -> ValidationResult:
        if observation.simulation_regression_failures > 0:
            return ValidationResult(False, ["simulation regression failures detected"])
        return ValidationResult(True)

    def performance_budget_checks(self, observation: Observation, frame_budget_ms_p95: float = 20.0) -> ValidationResult:
        if observation.frame_time_ms_p95 > frame_budget_ms_p95:
            return ValidationResult(
                False,
                [
                    f"frame-time budget exceeded: {observation.frame_time_ms_p95:.2f}ms > {frame_budget_ms_p95:.2f}ms"
                ],
            )
        return ValidationResult(True)

    def exploit_safety_checks(self, observation: Observation) -> ValidationResult:
        if observation.exploit_findings:
            findings = ", ".join(observation.exploit_findings)
            return ValidationResult(False, [f"exploit/safety findings present: {findings}"])
        return ValidationResult(True)

    def kpi_guard_checks(self, report: KPIReport) -> ValidationResult:
        reasons = []
        if self.kpi_calculator.below_threshold(report):
            reasons.append("KPI threshold floor violated")
        if self.kpi_calculator.regressed(report):
            reasons.append("KPI regression from baseline")
        return ValidationResult(not reasons, reasons)

    def validate_all(
        self,
        patch: PatchProposal,
        observation: Observation,
        kpi_report: KPIReport,
    ) -> ValidationResult:
        checks = [
            self.validate_patch_shape(patch),
            self.simulation_regression_checks(observation),
            self.performance_budget_checks(observation),
            self.exploit_safety_checks(observation),
            self.kpi_guard_checks(kpi_report),
        ]

        failures = [reason for check in checks if not check.passed for reason in check.reasons]
        return ValidationResult(passed=not failures, reasons=failures)
