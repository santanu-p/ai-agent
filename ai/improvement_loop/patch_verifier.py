from __future__ import annotations

import subprocess
from dataclasses import dataclass, field


@dataclass(slots=True)
class VerificationCheck:
    name: str
    command: str
    passed: bool
    output: str


@dataclass(slots=True)
class VerificationResult:
    passed: bool
    checks: list[VerificationCheck] = field(default_factory=list)


class PatchVerifier:
    """Runs static checks and simulation tests for candidate patches."""

    def __init__(self, static_checks: list[str] | None = None, sim_tests: list[str] | None = None) -> None:
        self.static_checks = static_checks or []
        self.sim_tests = sim_tests or []

    def verify(self) -> VerificationResult:
        checks: list[VerificationCheck] = []

        for command in self.static_checks:
            checks.append(self._run_command("static", command))

        for command in self.sim_tests:
            checks.append(self._run_command("simulation", command))

        passed = all(item.passed for item in checks) if checks else True
        return VerificationResult(passed=passed, checks=checks)

    def _run_command(self, kind: str, command: str) -> VerificationCheck:
        proc = subprocess.run(
            command,
            shell=True,
            check=False,
            text=True,
            capture_output=True,
        )
        output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        return VerificationCheck(
            name=f"{kind}:{command}",
            command=command,
            passed=proc.returncode == 0,
            output=output.strip(),
        )
