"""Build training-ready datasets from telemetry logs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


@dataclass
class DatasetSample:
    trajectory: List[Dict[str, Any]]
    label: str
    reward: float


class DatasetBuilder:
    """Transforms event logs into supervised/RL-ready samples."""

    def __init__(self, window_size: int = 10, stride: int = 1) -> None:
        self.window_size = max(1, window_size)
        self.stride = max(1, stride)

    def read_events(self, log_path: str | Path) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        with Path(log_path).open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    events.append(json.loads(line))
        events.sort(key=lambda item: item.get("timestamp", ""))
        return events

    def build_samples(self, events: Iterable[Dict[str, Any]]) -> List[DatasetSample]:
        by_session: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for event in events:
            by_session[event["session_id"]].append(event)

        samples: List[DatasetSample] = []
        for session_events in by_session.values():
            session_events.sort(key=lambda item: item.get("timestamp", ""))
            samples.extend(self._session_to_samples(session_events))
        return samples

    def persist_dataset(self, samples: List[DatasetSample], output_path: str | Path) -> None:
        payload = [
            {
                "trajectory": sample.trajectory,
                "label": sample.label,
                "reward": sample.reward,
            }
            for sample in samples
        ]
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def build_from_log(self, log_path: str | Path, output_path: str | Path) -> List[DatasetSample]:
        events = self.read_events(log_path)
        samples = self.build_samples(events)
        self.persist_dataset(samples, output_path)
        return samples

    def _session_to_samples(self, session_events: List[Dict[str, Any]]) -> List[DatasetSample]:
        samples: List[DatasetSample] = []
        if len(session_events) < self.window_size + 1:
            return samples

        for start in range(0, len(session_events) - self.window_size, self.stride):
            end = start + self.window_size
            window = session_events[start:end]
            target_event = session_events[end]
            label, reward = self._derive_label_reward(window, target_event)
            samples.append(DatasetSample(trajectory=window, label=label, reward=reward))

        return samples

    def _derive_label_reward(
        self,
        trajectory: List[Dict[str, Any]],
        target_event: Dict[str, Any],
    ) -> Tuple[str, float]:
        event_type = target_event["event_type"]
        payload = target_event.get("payload", {})

        if event_type == "npc_outcome":
            label = str(payload.get("result", "unknown"))
            reward = float(payload.get("score_delta", 0.0))
        elif event_type == "quest_completion":
            label = "quest_complete"
            reward = float(payload.get("xp_reward", 1.0))
        elif event_type == "death_cause":
            label = f"death:{payload.get('cause', 'unknown')}"
            reward = -abs(float(payload.get("penalty", 1.0)))
        elif event_type == "economy_metric":
            label = "economy_update"
            reward = float(payload.get("net_value_change", 0.0))
        else:
            label = str(payload.get("action", event_type))
            reward = float(payload.get("engagement_score", 0.0))

        if any(event["event_type"] == "death_cause" for event in trajectory):
            reward -= 0.25

        return label, reward


__all__ = ["DatasetBuilder", "DatasetSample"]
