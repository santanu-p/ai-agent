"""Policy definitions for constrained self-rebuild changes."""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ChangeSpec:
    """Defines what automated rebuilds are allowed to change."""

    allowed_paths: Sequence[str]
    allowed_apis: Sequence[str] = field(default_factory=tuple)
    forbidden_files: Sequence[str] = field(default_factory=tuple)
    max_diff_bytes: int = 200_000
    max_changed_files: int = 25

    def is_path_allowed(self, path: str) -> bool:
        normalized = path.strip()
        if any(fnmatch(normalized, pattern) for pattern in self.forbidden_files):
            return False
        return any(fnmatch(normalized, pattern) for pattern in self.allowed_paths)

    def validate_changed_paths(self, changed_paths: Iterable[str]) -> list[str]:
        violations: list[str] = []
        paths = list(changed_paths)

        if len(paths) > self.max_changed_files:
            violations.append(
                f"Changed files {len(paths)} exceeds max_changed_files={self.max_changed_files}."
            )

        for path in paths:
            if not self.is_path_allowed(path):
                violations.append(f"Path not allowed by policy: {path}")

        return violations

    def validate_diff(self, diff_text: str) -> list[str]:
        violations: list[str] = []

        if len(diff_text.encode("utf-8")) > self.max_diff_bytes:
            violations.append(
                f"Diff size exceeds max_diff_bytes={self.max_diff_bytes}."
            )

        changed_paths = extract_changed_paths(diff_text)
        violations.extend(self.validate_changed_paths(changed_paths))

        return violations


@dataclass(frozen=True)
class ApiChangeGuard:
    """Simple API guardrail based on protected tokens/signatures."""

    protected_tokens: Sequence[str] = field(default_factory=tuple)

    def check_source(self, before: str, after: str) -> list[str]:
        violations: list[str] = []
        for token in self.protected_tokens:
            if token in before and token not in after:
                violations.append(f"Protected API token removed: {token}")
        return violations


def extract_changed_paths(diff_text: str) -> list[str]:
    """Extract changed paths from a unified diff."""

    changed: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            path = line.removeprefix("+++ b/").strip()
            if path and path != "/dev/null":
                changed.append(path)
    # preserve order and remove duplicates
    return list(dict.fromkeys(changed))


def ensure_paths_exist(repo_root: Path, paths: Iterable[str]) -> list[str]:
    missing: list[str] = []
    for path in paths:
        if not (repo_root / path).exists():
            missing.append(path)
    return missing
