"""Orchestrates a constrained and safe self-rebuild lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Callable, Sequence

from .change_spec import ChangeSpec
from .patch_generator import CandidatePatch, ImprovementGoal, PatchGenerator, TelemetrySnapshot
from .rollback import RollbackManager
from .validators import ValidationReport, Validators


@dataclass(frozen=True)
class ProvenanceMetadata:
    model_version: str
    prompt_hash: str
    patch_digest: str
    evaluation_report: dict
    created_at: str
    signature: str


@dataclass(frozen=True)
class DeploymentConfig:
    style_commands: Sequence[str]
    replay_command: str
    save_compat_command: str
    crash_perf_command: str
    canary_deploy_command: str
    full_deploy_command: str


@dataclass(frozen=True)
class OrchestrationResult:
    applied: bool
    reason: str
    selected_goal_id: str | None = None
    validation_report_path: str | None = None
    provenance_path: str | None = None


class AutoRebuildOrchestrator:
    def __init__(
        self,
        *,
        repo_root: Path,
        change_spec: ChangeSpec,
        patch_generator: PatchGenerator,
        validators: Validators,
        rollback_manager: RollbackManager,
        model_version: str,
        signing_key: str,
    ):
        self.repo_root = repo_root
        self.change_spec = change_spec
        self.patch_generator = patch_generator
        self.validators = validators
        self.rollback_manager = rollback_manager
        self.model_version = model_version
        self.signing_key = signing_key.encode("utf-8")

    def run_cycle(
        self,
        *,
        goals: Sequence[ImprovementGoal],
        telemetry: Sequence[TelemetrySnapshot],
        operator_prompt: str,
        deploy: DeploymentConfig,
    ) -> OrchestrationResult:
        candidates = self.patch_generator.generate_candidates(goals, telemetry)
        if not candidates:
            return OrchestrationResult(applied=False, reason="No candidate patches were generated.")

        selected = candidates[0]
        policy_violations = self.change_spec.validate_diff(selected.diff)
        if policy_violations:
            return OrchestrationResult(
                applied=False,
                reason="Policy gate failed: " + "; ".join(policy_violations),
                selected_goal_id=selected.goal_id,
            )

        last_good = self.rollback_manager.capture_last_known_good()

        try:
            self._apply_patch(selected)
            report = self.validators.run_all(
                style_commands=deploy.style_commands,
                replay_command=deploy.replay_command,
                save_compat_command=deploy.save_compat_command,
                crash_perf_command=deploy.crash_perf_command,
            )
            report_path = self.repo_root / ".self_rebuild" / "reports" / "validation.json"
            self.validators.persist_report(report, report_path)

            if not report.passed:
                self.rollback_manager.rollback(last_good)
                return OrchestrationResult(
                    applied=False,
                    reason="Validation gates failed.",
                    selected_goal_id=selected.goal_id,
                    validation_report_path=str(report_path),
                )

            self._run(deploy.canary_deploy_command)
            self._run(deploy.full_deploy_command)

            post_deploy_gate = self.validators.run_crash_perf_budget(deploy.crash_perf_command)
            if not post_deploy_gate.passed:
                self.rollback_manager.rollback(last_good)
                return OrchestrationResult(
                    applied=False,
                    reason="Post-deploy crash/perf gate failed; rolled back.",
                    selected_goal_id=selected.goal_id,
                    validation_report_path=str(report_path),
                )

            provenance = self._build_provenance(
                selected=selected,
                prompt=operator_prompt,
                report=report,
            )
            provenance_path = self._persist_provenance(provenance)
            self.rollback_manager.mark_last_known_good()

            return OrchestrationResult(
                applied=True,
                reason="Patch applied and deployed.",
                selected_goal_id=selected.goal_id,
                validation_report_path=str(report_path),
                provenance_path=str(provenance_path),
            )
        except Exception as exc:  # noqa: BLE001 - orchestrator must fail closed
            self.rollback_manager.rollback(last_good)
            return OrchestrationResult(
                applied=False,
                reason=f"Exception during cycle; rolled back. {exc}",
                selected_goal_id=selected.goal_id,
            )

    def _apply_patch(self, candidate: CandidatePatch) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as temp_patch:
            temp_patch.write(candidate.diff)
            patch_path = Path(temp_patch.name)

        try:
            self._run(f"git apply --check {patch_path}")
            self._run(f"git apply {patch_path}")
        finally:
            patch_path.unlink(missing_ok=True)

        # defensive verify against policy drift after application
        changed = self._changed_paths()
        violations = self.change_spec.validate_changed_paths(changed)
        if violations:
            raise RuntimeError("; ".join(violations))

    def _changed_paths(self) -> list[str]:
        output = self._run("git diff --name-only")
        return [line.strip() for line in output.splitlines() if line.strip()]

    def _build_provenance(
        self,
        *,
        selected: CandidatePatch,
        prompt: str,
        report: ValidationReport,
    ) -> ProvenanceMetadata:
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        patch_digest = hashlib.sha256(selected.diff.encode("utf-8")).hexdigest()
        evaluation_report = report.as_dict()
        created_at = datetime.now(timezone.utc).isoformat()

        signed_payload = json.dumps(
            {
                "model_version": self.model_version,
                "prompt_hash": prompt_hash,
                "patch_digest": patch_digest,
                "evaluation_report": evaluation_report,
                "created_at": created_at,
            },
            sort_keys=True,
        ).encode("utf-8")

        signature = hmac.new(self.signing_key, signed_payload, hashlib.sha256).hexdigest()

        return ProvenanceMetadata(
            model_version=self.model_version,
            prompt_hash=prompt_hash,
            patch_digest=patch_digest,
            evaluation_report=evaluation_report,
            created_at=created_at,
            signature=signature,
        )

    def _persist_provenance(self, provenance: ProvenanceMetadata) -> Path:
        out_dir = self.repo_root / ".self_rebuild" / "provenance"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = out_dir / f"{ts}.json"
        path.write_text(json.dumps(provenance.__dict__, indent=2), encoding="utf-8")
        return path

    def _run(self, command: str) -> str:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Command failed: {command}\n{proc.stdout}\n{proc.stderr}")
        return ((proc.stdout or "") + (proc.stderr or "")).strip()
