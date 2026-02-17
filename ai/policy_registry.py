"""Policy versioning, rollout state, and canary promotion control plane."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

RolloutStatus = Literal["shadow", "canary", "promoted", "rolled_back"]


@dataclass
class PolicyRecord:
    policy_id: str
    semver: str
    artifact_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    rollout_status: RolloutStatus = "shadow"
    canary_percent: int = 0
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))


class PolicyRegistry:
    """Persistent registry for policy lifecycle operations."""

    def __init__(self, registry_path: str | Path) -> None:
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self._save({"policies": [], "active_policy_id": None, "history": []})

    def register_policy(
        self,
        policy_id: str,
        semver: str,
        artifact_path: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PolicyRecord:
        state = self._load()
        record = PolicyRecord(
            policy_id=policy_id,
            semver=semver,
            artifact_path=artifact_path,
            metadata=metadata or {},
        )
        state["policies"].append(record.__dict__)
        self._save(state)
        return record

    def start_canary(self, policy_id: str, percent: int = 5) -> None:
        state = self._load()
        record = self._find_policy(state, policy_id)
        record["rollout_status"] = "canary"
        record["canary_percent"] = max(1, min(50, percent))
        self._save(state)

    def evaluate_canary(self, policy_id: str, baseline_metrics: Dict[str, float], canary_metrics: Dict[str, float]) -> str:
        """Compare canary vs baseline metrics and promote or rollback.

        Returns either "promoted" or "rolled_back".
        """
        baseline = baseline_metrics.get("score", 0.0)
        candidate = canary_metrics.get("score", 0.0)
        regression = canary_metrics.get("exploit_risk", 0.0) > baseline_metrics.get("exploit_risk", 0.0) + 0.03

        decision = "rolled_back"
        if candidate >= baseline and not regression:
            self.promote(policy_id)
            decision = "promoted"
        else:
            self.rollback(policy_id)

        state = self._load()
        state.setdefault("history", []).append(
            {
                "policy_id": policy_id,
                "decision": decision,
                "baseline_metrics": baseline_metrics,
                "canary_metrics": canary_metrics,
                "timestamp_ms": int(time.time() * 1000),
            }
        )
        self._save(state)
        return decision

    def promote(self, policy_id: str) -> None:
        state = self._load()
        record = self._find_policy(state, policy_id)
        record["rollout_status"] = "promoted"
        record["canary_percent"] = 100
        state["active_policy_id"] = policy_id
        self._save(state)

    def rollback(self, policy_id: str) -> None:
        state = self._load()
        record = self._find_policy(state, policy_id)
        record["rollout_status"] = "rolled_back"
        record["canary_percent"] = 0
        self._save(state)

    def get_active_policy(self) -> Optional[Dict[str, Any]]:
        state = self._load()
        active = state.get("active_policy_id")
        if not active:
            return None
        return self._find_policy(state, active)

    def list_policies(self) -> List[Dict[str, Any]]:
        return list(self._load().get("policies", []))

    def _find_policy(self, state: Dict[str, Any], policy_id: str) -> Dict[str, Any]:
        for record in state.get("policies", []):
            if record.get("policy_id") == policy_id:
                return record
        raise KeyError(f"Unknown policy_id={policy_id!r}")

    def _load(self) -> Dict[str, Any]:
        with self.registry_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def _save(self, state: Dict[str, Any]) -> None:
        with self.registry_path.open("w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
