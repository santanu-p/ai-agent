"""Validation gates used by the self-rebuild orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import subprocess
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    command: str
    output: str


@dataclass
class ValidationReport:
    gates: list[GateResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(g.passed for g in self.gates)

    def add(self, gate: GateResult) -> None:
        self.gates.append(gate)

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "gates": [
                {
                    "name": gate.name,
                    "passed": gate.passed,
                    "command": gate.command,
                    "output": gate.output,
                }
                for gate in self.gates
            ],
        }


class ValidationError(RuntimeError):
    pass


class Validators:
    """Mandatory gates for safe autonomous patch application."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def run_all(
        self,
        *,
        style_commands: Sequence[str],
        replay_command: str,
        save_compat_command: str,
        crash_perf_command: str,
    ) -> ValidationReport:
        report = ValidationReport()

        report.add(self.run_style_lint_type(style_commands))
        report.add(self.run_deterministic_replay(replay_command))
        report.add(self.run_save_compatibility(save_compat_command))
        report.add(self.run_crash_perf_budget(crash_perf_command))

        return report

    def run_style_lint_type(self, commands: Iterable[str]) -> GateResult:
        outputs: list[str] = []
        for cmd in commands:
            rc, out = self._run(cmd)
            outputs.append(f"$ {cmd}\n{out}")
            if rc != 0:
                return GateResult(
                    name="style_lint_type",
                    passed=False,
                    command=" && ".join(commands),
                    output="\n\n".join(outputs),
                )
        return GateResult(
            name="style_lint_type",
            passed=True,
            command=" && ".join(commands),
            output="\n\n".join(outputs),
        )

    def run_deterministic_replay(self, command: str) -> GateResult:
        rc, out = self._run(command)
        return GateResult(
            name="deterministic_replay",
            passed=rc == 0,
            command=command,
            output=out,
        )

    def run_save_compatibility(self, command: str) -> GateResult:
        rc, out = self._run(command)
        return GateResult(
            name="save_compatibility",
            passed=rc == 0,
            command=command,
            output=out,
        )

    def run_crash_perf_budget(self, command: str) -> GateResult:
        rc, out = self._run(command)
        return GateResult(
            name="crash_perf_budget",
            passed=rc == 0,
            command=command,
            output=out,
        )

    def persist_report(self, report: ValidationReport, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")

    def _run(self, command: str) -> tuple[int, str]:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, output.strip()
