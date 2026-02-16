from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .objective_evaluator import FitnessScore
from .telemetry_collector import MetricsSnapshot


@dataclass(slots=True)
class PatchProposal:
    prompt_version: str
    prompt: str
    proposed_diff: str
    target_files: list[str]


class PatchGenerator:
    """Requests constrained config/code patches from a model client."""

    def __init__(self, model_client: Any, prompt_version: str = "v1") -> None:
        self.model_client = model_client
        self.prompt_version = prompt_version

    def propose_patch(
        self,
        snapshot: MetricsSnapshot,
        fitness: FitnessScore,
        constraints: list[str],
        target_files: list[str],
    ) -> PatchProposal:
        constraint_block = "\n".join(f"- {item}" for item in constraints)
        target_block = "\n".join(f"- {item}" for item in target_files)

        prompt = (
            "You are a game-balance patch assistant.\n"
            "Generate a minimal unified diff that improves objectives while following all constraints.\n\n"
            f"Prompt version: {self.prompt_version}\n"
            f"Current fitness: {fitness.total}\n"
            f"Fitness components: {fitness.components}\n"
            f"Metrics snapshot: {snapshot.to_dict()}\n"
            f"Allowed target files:\n{target_block}\n"
            f"Constraints:\n{constraint_block}\n"
            "Only return a unified diff."
        )

        proposed_diff = self.model_client.generate(prompt)
        return PatchProposal(
            prompt_version=self.prompt_version,
            prompt=prompt,
            proposed_diff=proposed_diff,
            target_files=target_files,
        )
