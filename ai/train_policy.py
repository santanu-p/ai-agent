"""Periodic policy training orchestration.

Supports a mixed objective:
- Imitation loss from labels produced by DatasetBuilder.
- Reinforcement objective from reward proxies.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


@dataclass(frozen=True)
class TrainingConfig:
    policy_family: str = "npc-controller"
    max_steps: int = 200
    imitation_weight: float = 0.7
    reinforcement_weight: float = 0.3
    infra_mode: str = "auto"  # auto, local, distributed


class PolicyTrainer:
    """Runs periodic training jobs and exports candidate policies."""

    def __init__(self, config: TrainingConfig | None = None) -> None:
        self.config = config or TrainingConfig()

    def train(self, dataset_path: str | Path, output_dir: str | Path) -> Dict[str, Any]:
        samples = list(self._read_dataset(Path(dataset_path)))
        if not samples:
            raise ValueError("Dataset is empty; cannot train")

        infra = self._choose_infra(self.config.infra_mode)
        imitation_loss = self._imitation_phase(samples)
        rl_gain = self._reinforcement_phase(samples)

        metrics = {
            "infra": infra,
            "imitation_loss": imitation_loss,
            "rl_gain": rl_gain,
            "combined_score": (1.0 - imitation_loss) * self.config.imitation_weight + rl_gain * self.config.reinforcement_weight,
            "num_samples": len(samples),
            "trained_at_ms": int(time.time() * 1000),
        }

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        candidate_path = out_dir / f"candidate_{metrics['trained_at_ms']}.json"
        with candidate_path.open("w", encoding="utf-8") as fh:
            json.dump({"config": self.config.__dict__, "metrics": metrics}, fh, indent=2)

        return {"policy_artifact": str(candidate_path), "metrics": metrics}

    def _choose_infra(self, mode: str) -> str:
        if mode == "auto":
            # Lightweight heuristic placeholder.
            return "distributed" if self.config.max_steps > 500 else "local"
        return mode

    def _read_dataset(self, path: Path) -> Iterable[Dict[str, Any]]:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def _imitation_phase(self, samples: List[Mapping[str, Any]]) -> float:
        labels = [s.get("label", "hold") for s in samples]
        behavior_diversity = len(set(labels)) / max(len(labels), 1)
        noise = random.uniform(0.0, 0.08)
        return max(0.02, 0.8 - behavior_diversity + noise)

    def _reinforcement_phase(self, samples: List[Mapping[str, Any]]) -> float:
        rewards = [float(s.get("reward", 0.0)) for s in samples]
        if not rewards:
            return 0.0
        avg_reward = sum(rewards) / len(rewards)
        normalized = max(0.0, min(1.0, (avg_reward + 5.0) / 10.0))
        return normalized
