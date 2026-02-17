from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import GeneratedPatch, MetricsSnapshot, ObjectiveScores


class PatchModelClient(Protocol):
    def complete(self, prompt: str) -> str:
        """Return a unified diff based on the prompt constraints."""


@dataclass
class PatchConstraints:
    max_files: int = 5
    allow_code_changes: bool = True
    allow_config_changes: bool = True


class PatchGenerator:
    """Builds constrained patch prompts and queries model for candidate diff."""

    def __init__(
        self,
        model_client: PatchModelClient,
        prompt_version: str = "v1",
        constraints: PatchConstraints | None = None,
    ) -> None:
        self.model_client = model_client
        self.prompt_version = prompt_version
        self.constraints = constraints or PatchConstraints()

    def build_prompt(self, metrics: MetricsSnapshot, scores: ObjectiveScores) -> str:
        return (
            f"Prompt version: {self.prompt_version}\n"
            "Task: Improve gameplay KPIs with a minimal patch.\n"
            "Output: unified diff only.\n"
            f"Constraints: max_files={self.constraints.max_files}, "
            f"allow_code_changes={self.constraints.allow_code_changes}, "
            f"allow_config_changes={self.constraints.allow_config_changes}.\n"
            f"Metrics: retention_d1={metrics.retention_d1:.3f}, retention_d7={metrics.retention_d7:.3f}, "
            f"quest_completion_rate={metrics.quest_completion_rate:.3f}, "
            f"economy_inflation_index={metrics.economy_inflation_index:.3f}, "
            f"top_death_causes={metrics.top_death_causes}.\n"
            f"Objective scores: {scores.score_components}, overall={scores.overall_fitness:.3f}."
        )

    def generate(self, metrics: MetricsSnapshot, scores: ObjectiveScores) -> GeneratedPatch:
        prompt = self.build_prompt(metrics, scores)
        diff = self.model_client.complete(prompt)
        targets = []
        for line in diff.splitlines():
            if line.startswith("+++ b/"):
                targets.append(line.replace("+++ b/", "", 1))
        return GeneratedPatch(
            prompt_version=self.prompt_version,
            prompt_text=prompt,
            diff=diff,
            target_files=targets,
        )
