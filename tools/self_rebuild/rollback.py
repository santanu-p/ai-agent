"""Rollback helpers for reverting to last known-good state."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RollbackState:
    commit_sha: str
    policy_snapshot: Path


class RollbackManager:
    """Tracks and restores the last known good build and policy snapshot."""

    def __init__(self, repo_root: Path, state_dir: Path) -> None:
        self.repo_root = repo_root
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

    @property
    def policy_backup_path(self) -> Path:
        return self.state_dir / "last_good_policy.json"

    @property
    def commit_backup_path(self) -> Path:
        return self.state_dir / "last_good_commit.txt"

    def snapshot(self, policy_path: Path) -> RollbackState:
        commit_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.repo_root, text=True
        ).strip()
        shutil.copyfile(policy_path, self.policy_backup_path)
        self.commit_backup_path.write_text(commit_sha, encoding="utf-8")
        return RollbackState(commit_sha=commit_sha, policy_snapshot=self.policy_backup_path)

    def rollback(self, restore_policy_path: Path) -> str:
        """Restore git state and policy to last known-good snapshot."""

        if not self.commit_backup_path.exists() or not self.policy_backup_path.exists():
            raise FileNotFoundError("Rollback state not found.")
        commit_sha = self.commit_backup_path.read_text(encoding="utf-8").strip()
        subprocess.run(["git", "reset", "--hard", commit_sha], cwd=self.repo_root, check=True)
        shutil.copyfile(self.policy_backup_path, restore_policy_path)
        return commit_sha
