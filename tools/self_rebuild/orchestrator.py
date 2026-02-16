"""Orchestrates constrained auto-rebuild cycles with safe deployment controls."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .change_spec import ChangeSpec, DEFAULT_CHANGE_SPEC
from .patch_generator import PatchCandidate, PatchGenerator
from .rollback import RollbackManager
from .validators import Validators


@dataclass(frozen=True)
class ProvenanceMetadata:
    model_version: str
    prompt_hash: str
    evaluation_report: dict[str, Any]


class SelfRebuildOrchestrator:
    """Runs: generate patch -> checks -> sandbox validation -> staged deploy."""

    def __init__(
        self,
        repo_root: Path,
        *,
        model_version: str,
        change_spec: ChangeSpec = DEFAULT_CHANGE_SPEC,
        state_dir: Path | None = None,
    ) -> None:
        self.repo_root = repo_root
        self.change_spec = change_spec
        self.validators = Validators(repo_root)
        self.patch_generator = PatchGenerator(repo_root, change_spec, model_version)
        self.state_dir = state_dir or repo_root / ".self_rebuild_state"
        self.rollback_manager = RollbackManager(repo_root, self.state_dir)

    @property
    def provenance_dir(self) -> Path:
        path = self.state_dir / "provenance"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _sandbox_validation(self) -> None:
        """Run candidate in a disposable sandbox command."""

        subprocess.run(["bash", "scripts/sandbox_validate.sh"], cwd=self.repo_root, check=True)

    def _staged_deploy(self) -> None:
        """Promote validated candidate using staged deployment controls."""

        subprocess.run(["bash", "scripts/staged_deploy.sh"], cwd=self.repo_root, check=True)

    def _write_provenance(self, candidate: PatchCandidate, report: dict[str, Any]) -> Path:
        metadata = ProvenanceMetadata(
            model_version=candidate.model_version,
            prompt_hash=candidate.prompt_hash,
            evaluation_report=report,
        )
        target = self.provenance_dir / f"{candidate.prompt_hash}.json"
        target.write_text(json.dumps(metadata.__dict__, indent=2), encoding="utf-8")
        return target

    def run_cycle(self, goal: str, telemetry: dict[str, Any], *, diff_text: str, policy_path: Path) -> dict[str, Any]:
        """Execute the constrained self-rebuild workflow end-to-end."""

        self.rollback_manager.snapshot(policy_path)
        candidate = self.patch_generator.generate_candidate(goal, telemetry, diff_text=diff_text)
        changed_paths = self.patch_generator.changed_paths_from_diff(candidate.diff_text)
        self.change_spec.validate_changed_paths(self.repo_root, changed_paths)

        self.patch_generator.apply_patch_to_worktree(candidate.diff_text)

        validation_results = self.validators.run_all()
        report = self.validators.as_report(validation_results)
        if not report["all_passed"]:
            self.rollback_manager.rollback(policy_path)
            raise RuntimeError("Validation gates failed; rollback completed.")

        self._sandbox_validation()
        self._staged_deploy()

        post_deploy_results = self.validators.run_all()
        post_deploy_report = self.validators.as_report(post_deploy_results)
        if not post_deploy_report["all_passed"]:
            reverted = self.rollback_manager.rollback(policy_path)
            raise RuntimeError(f"Post-deploy checks failed; rolled back to {reverted}.")

        provenance_path = self._write_provenance(candidate, post_deploy_report)
        return {
            "status": "deployed",
            "provenance": provenance_path.as_posix(),
            "report": post_deploy_report,
        }
