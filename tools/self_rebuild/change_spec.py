"""Policy objects describing what self-rebuild is allowed to change."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ChangeSpec:
    """Defines hard constraints for AI-authored patches."""

    allowed_paths: tuple[str, ...]
    allowed_apis: tuple[str, ...] = ()
    forbidden_files: tuple[str, ...] = ()
    max_diff_lines: int = 500

    def is_path_allowed(self, repo_root: Path, file_path: Path) -> bool:
        """Return True only when the file lives in a configured allow-list path."""

        rel = file_path.resolve().relative_to(repo_root.resolve())
        rel_str = rel.as_posix()
        if any(rel_str == forbidden or rel_str.startswith(f"{forbidden}/") for forbidden in self.forbidden_files):
            return False
        return any(rel_str == allowed or rel_str.startswith(f"{allowed}/") for allowed in self.allowed_paths)

    def validate_changed_paths(self, repo_root: Path, changed_paths: Iterable[Path]) -> None:
        """Raise when a path falls outside configured constraints."""

        disallowed = [path for path in changed_paths if not self.is_path_allowed(repo_root, path)]
        if disallowed:
            formatted = ", ".join(sorted(path.as_posix() for path in disallowed))
            raise ValueError(f"Patch touches disallowed files: {formatted}")

    def validate_diff_size(self, unified_diff_text: str) -> None:
        """Raise when a patch exceeds line-count budget."""

        line_count = sum(
            1
            for line in unified_diff_text.splitlines()
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
        )
        if line_count > self.max_diff_lines:
            raise ValueError(
                f"Patch too large: changed {line_count} lines, budget is {self.max_diff_lines}."
            )


DEFAULT_CHANGE_SPEC = ChangeSpec(
    allowed_paths=("tools/self_rebuild",),
    allowed_apis=(
        "tools.self_rebuild.orchestrator",
        "tools.self_rebuild.change_spec",
        "tools.self_rebuild.patch_generator",
        "tools.self_rebuild.validators",
        "tools.self_rebuild.rollback",
    ),
    forbidden_files=(
        ".git",
        ".env",
        "secrets",
        "production",
    ),
    max_diff_lines=800,
)
