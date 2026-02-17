from __future__ import annotations

import subprocess
from typing import Sequence

from .models import GeneratedPatch, PatchProposal, VerificationResults, as_generated_patch


class PatchVerifier:
    """Runs static and simulation checks for generated patches."""

    def __init__(
        self,
        static_checks: Sequence[str] | None = None,
        simulation_checks: Sequence[str] | None = None,
        workdir: str = ".",
    ) -> None:
        self.static_checks = list(static_checks or ["python -m compileall ai"])
        self.simulation_checks = list(simulation_checks or ["python -m unittest discover -s tests"])
        self.workdir = workdir

    def _run_commands(self, commands: Sequence[str]) -> tuple[bool, str]:
        outputs = []
        all_passed = True
        for command in commands:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=self.workdir,
                capture_output=True,
                text=True,
            )
            outputs.append(f"$ {command}\n{proc.stdout}{proc.stderr}".strip())
            if proc.returncode != 0:
                all_passed = False
        return all_passed, "\n\n".join(outputs)

    def verify(self, patch: GeneratedPatch | PatchProposal) -> VerificationResults:
        _ = as_generated_patch(patch)
        static_ok, static_report = self._run_commands(self.static_checks)
        sim_ok, sim_report = self._run_commands(self.simulation_checks)
        return VerificationResults(
            static_checks_passed=static_ok,
            simulation_checks_passed=sim_ok,
            static_check_report=static_report,
            simulation_report=sim_report,
        )
