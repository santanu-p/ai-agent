"""Validation gates that every self-rebuild candidate must pass."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationResult:
    gate: str
    passed: bool
    details: str
    duration_s: float


class Validators:
    """Runs all mandatory quality and safety gates."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def _run(self, gate: str, command: list[str]) -> ValidationResult:
        start = time.time()
        proc = subprocess.run(
            command,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
        )
        duration = time.time() - start
        passed = proc.returncode == 0
        details = (proc.stdout + "\n" + proc.stderr).strip()
        return ValidationResult(gate=gate, passed=passed, details=details, duration_s=duration)

    def style_lint_type_checks(self) -> ValidationResult:
        """Run style/lint/type checks.

        Expects a repository-provided command named `scripts/checks.sh`.
        """

        return self._run("style_lint_type", ["bash", "scripts/checks.sh"])

    def deterministic_simulation_replay_check(self) -> ValidationResult:
        """Ensure deterministic replay of simulations."""

        return self._run("deterministic_replay", ["bash", "scripts/replay_check.sh"])

    def save_compatibility_check(self) -> ValidationResult:
        """Verify save/backward compatibility guarantees."""

        return self._run("save_compatibility", ["bash", "scripts/save_compat_check.sh"])

    def crash_perf_budget_check(self) -> ValidationResult:
        """Verify crash-free and performance budget limits."""

        return self._run("crash_perf_budget", ["bash", "scripts/perf_budget_check.sh"])

    def run_all(self) -> list[ValidationResult]:
        """Run all mandatory gates in required order."""

        results = [
            self.style_lint_type_checks(),
            self.deterministic_simulation_replay_check(),
            self.save_compatibility_check(),
            self.crash_perf_budget_check(),
        ]
        return results

    @staticmethod
    def as_report(results: list[ValidationResult]) -> dict:
        """Serialize results for provenance metadata."""

        return {
            "all_passed": all(result.passed for result in results),
            "gates": [
                {
                    "gate": result.gate,
                    "passed": result.passed,
                    "duration_s": round(result.duration_s, 3),
                    "details": result.details,
                }
                for result in results
            ],
        }

    @staticmethod
    def write_report(path: Path, results: list[ValidationResult]) -> None:
        path.write_text(json.dumps(Validators.as_report(results), indent=2), encoding="utf-8")
