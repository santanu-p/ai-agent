"""Generate candidate patch proposals under policy constraints."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .change_spec import ChangeSpec


@dataclass(frozen=True)
class PatchCandidate:
    """A generated patch and the metadata used to evaluate it."""

    diff_text: str
    goal: str
    telemetry: dict[str, Any]
    model_version: str
    prompt_hash: str


def _hash_prompt(goal: str, telemetry: dict[str, Any]) -> str:
    payload = json.dumps({"goal": goal, "telemetry": telemetry}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class PatchGenerator:
    """Creates candidate diffs from an improvement goal and telemetry summary.

    This implementation intentionally keeps the generation mechanism pluggable.
    The default strategy creates an editable prompt artifact that can be consumed
    by an external code model and expects the resulting patch in unified diff form.
    """

    def __init__(self, repo_root: Path, change_spec: ChangeSpec, model_version: str) -> None:
        self.repo_root = repo_root
        self.change_spec = change_spec
        self.model_version = model_version

    def build_generation_prompt(self, goal: str, telemetry: dict[str, Any]) -> str:
        """Build a deterministic prompt with policy constraints included."""

        return (
            "You are proposing a unified diff patch.\n"
            f"Goal: {goal}\n"
            f"Allowed paths: {', '.join(self.change_spec.allowed_paths)}\n"
            f"Allowed APIs: {', '.join(self.change_spec.allowed_apis)}\n"
            f"Forbidden files: {', '.join(self.change_spec.forbidden_files)}\n"
            f"Max changed lines: {self.change_spec.max_diff_lines}\n"
            f"Telemetry: {json.dumps(telemetry, sort_keys=True)}\n"
            "Emit only a unified diff."
        )

    def generate_candidate(self, goal: str, telemetry: dict[str, Any], *, diff_text: str) -> PatchCandidate:
        """Construct and validate a candidate from externally-produced diff text."""

        self.change_spec.validate_diff_size(diff_text)
        return PatchCandidate(
            diff_text=diff_text,
            goal=goal,
            telemetry=telemetry,
            model_version=self.model_version,
            prompt_hash=_hash_prompt(goal, telemetry),
        )

    def changed_paths_from_diff(self, diff_text: str) -> list[Path]:
        """Parse changed file paths from a unified diff."""

        paths: list[Path] = []
        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                rel = line.removeprefix("+++ b/").strip()
                if rel != "/dev/null":
                    paths.append(self.repo_root / rel)
        return paths

    def apply_patch_to_worktree(self, diff_text: str) -> None:
        """Apply unified diff into the current worktree."""

        subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "-"],
            input=diff_text.encode("utf-8"),
            cwd=self.repo_root,
            check=True,
        )
