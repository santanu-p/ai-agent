"""Builds training datasets from raw AI telemetry logs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Sequence


@dataclass(frozen=True)
class TrajectorySample:
    """Windowed trajectory used for policy learning."""

    entity_id: str
    match_id: str
    start_timestamp_ms: int
    end_timestamp_ms: int
    observations: List[Dict[str, Any]]
    label: str
    reward: float


class DatasetBuilder:
    """Transforms JSONL event logs into windowed trajectory samples."""

    def __init__(self, window_size: int = 8, stride: int = 4) -> None:
        if window_size <= 0:
            raise ValueError("window_size must be positive")
        if stride <= 0:
            raise ValueError("stride must be positive")
        self.window_size = window_size
        self.stride = stride

    def build(self, log_path: str | Path, output_path: str | Path) -> int:
        """Read logs, construct trajectories, and emit JSONL dataset."""
        events = list(self._read_events(Path(log_path)))
        grouped = self._group_by_entity(events)
        samples: List[TrajectorySample] = []
        for _, entity_events in grouped.items():
            samples.extend(self._build_entity_samples(entity_events))

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as fh:
            for sample in samples:
                fh.write(json.dumps(sample.__dict__, separators=(",", ":")) + "\n")
        return len(samples)

    def _read_events(self, path: Path) -> Iterator[Dict[str, Any]]:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)

    def _group_by_entity(self, events: Sequence[Mapping[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for event in sorted(events, key=lambda e: e.get("timestamp_ms", 0)):
            key = f"{event.get('match_id', '')}:{event.get('entity_id', '')}"
            grouped.setdefault(key, []).append(dict(event))
        return grouped

    def _build_entity_samples(self, events: Sequence[Mapping[str, Any]]) -> Iterable[TrajectorySample]:
        if len(events) < self.window_size:
            return []

        samples: List[TrajectorySample] = []
        for start in range(0, len(events) - self.window_size + 1, self.stride):
            window = events[start : start + self.window_size]
            label = self._derive_label(window)
            reward = self._derive_reward(window)
            sample = TrajectorySample(
                entity_id=str(window[-1].get("entity_id", "")),
                match_id=str(window[-1].get("match_id", "")),
                start_timestamp_ms=int(window[0].get("timestamp_ms", 0)),
                end_timestamp_ms=int(window[-1].get("timestamp_ms", 0)),
                observations=[dict(item) for item in window],
                label=label,
                reward=reward,
            )
            samples.append(sample)
        return samples

    def _derive_label(self, window: Sequence[Mapping[str, Any]]) -> str:
        """Simple behavior cloning target label for imitation learning."""
        for event in reversed(window):
            if event.get("event_type") == "npc_outcome":
                outcome = event.get("payload", {}).get("decision", "hold")
                return str(outcome)
        return "hold"

    def _derive_reward(self, window: Sequence[Mapping[str, Any]]) -> float:
        """Reward proxy from available telemetry, suitable for RL fine-tuning."""
        reward = 0.0
        for event in window:
            event_type = event.get("event_type")
            payload = event.get("payload", {})
            if event_type == "quest_completion":
                reward += float(payload.get("reward", 2.0))
            elif event_type == "npc_outcome":
                reward += float(payload.get("score_delta", 0.2))
            elif event_type == "death_cause":
                reward -= float(payload.get("penalty", 1.5))
            elif event_type == "economy_metric":
                reward += float(payload.get("stability_bonus", 0.0))
        return reward
