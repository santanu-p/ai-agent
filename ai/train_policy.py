"""Policy training entrypoints for periodic jobs."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class TrainingConfig:
    policy_id: str
    policy_version: str
    infra_mode: str = "local"  # local | distributed
    imitation_weight: float = 0.7
    reinforcement_weight: float = 0.3


class PolicyTrainer:
    """Hybrid trainer that combines imitation and reward-driven adjustment."""

    def __init__(self, config: TrainingConfig) -> None:
        self.config = config

    def train(self, dataset_path: str | Path, output_path: str | Path) -> Dict[str, Any]:
        samples = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
        if not samples:
            raise ValueError("Dataset is empty; cannot train policy")

        imitation = self._imitation_statistics(samples)
        reinforcement = self._reinforcement_statistics(samples)

        model = self._blend_objectives(imitation, reinforcement)
        artifact = {
            "policy_id": self.config.policy_id,
            "version": self.config.policy_version,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "infra_mode": self.config.infra_mode,
            "weights": {
                "imitation": self.config.imitation_weight,
                "reinforcement": self.config.reinforcement_weight,
            },
            "model": model,
        }

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
        return artifact

    def _imitation_statistics(self, samples: List[Dict[str, Any]]) -> Dict[str, float]:
        label_counts = Counter(sample["label"] for sample in samples)
        total = max(1, sum(label_counts.values()))
        return {label: count / total for label, count in label_counts.items()}

    def _reinforcement_statistics(self, samples: List[Dict[str, Any]]) -> Dict[str, float]:
        reward_sum = defaultdict(float)
        reward_count = defaultdict(int)
        for sample in samples:
            label = sample["label"]
            reward_sum[label] += float(sample.get("reward", 0.0))
            reward_count[label] += 1

        average_reward: Dict[str, float] = {}
        for label, total in reward_sum.items():
            average_reward[label] = total / max(1, reward_count[label])
        return average_reward

    def _blend_objectives(
        self,
        imitation: Dict[str, float],
        reinforcement: Dict[str, float],
    ) -> Dict[str, Any]:
        policy_scores: Dict[str, float] = {}
        for label in set(imitation) | set(reinforcement):
            imitation_score = imitation.get(label, 0.0)
            reward_score = reinforcement.get(label, 0.0)
            policy_scores[label] = (
                self.config.imitation_weight * imitation_score
                + self.config.reinforcement_weight * reward_score
            )

        ranking = sorted(policy_scores.items(), key=lambda item: item[1], reverse=True)
        return {
            "action_scores": policy_scores,
            "ranked_actions": [label for label, _ in ranking],
        }


__all__ = ["PolicyTrainer", "TrainingConfig"]
