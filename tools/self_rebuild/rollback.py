"""Rollback helpers for the self-rebuild workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


@dataclass(frozen=True)
class RollbackSnapshot:
    commit: str
    policy_backup_path: Path | None = None


class RollbackManager:
    def __init__(self, repo_root: Path, policy_path: Path | None = None):
        self.repo_root = repo_root
        self.policy_path = policy_path

    def capture_last_known_good(self) -> RollbackSnapshot:
        commit = self._git("rev-parse HEAD")
        backup_path: Path | None = None

        if self.policy_path and self.policy_path.exists():
            backup_path = self.repo_root / ".self_rebuild" / "policy.last_known_good"
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.policy_path, backup_path)

        return RollbackSnapshot(commit=commit, policy_backup_path=backup_path)

    def rollback(self, snapshot: RollbackSnapshot) -> None:
        self._git(f"reset --hard {snapshot.commit}")

        if self.policy_path and snapshot.policy_backup_path and snapshot.policy_backup_path.exists():
            shutil.copy2(snapshot.policy_backup_path, self.policy_path)

    def mark_last_known_good(self) -> str:
        return self._git("rev-parse HEAD")

    def _git(self, args: str) -> str:
        cmd = f"git {args}"
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Command failed: {cmd}\n{proc.stderr}")
        return (proc.stdout or "").strip()
