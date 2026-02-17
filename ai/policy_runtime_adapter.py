"""Runtime adapter for safe policy loading and canary rollouts."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .evaluate_policy import PolicyEvaluator
from .policy_registry import PolicyRegistry


class PolicyRuntimeAdapter:
    """Loads promoted/canary policies and serves decisions for NPC cohorts."""

    def __init__(self, registry: PolicyRegistry, evaluator: Optional[PolicyEvaluator] = None) -> None:
        self.registry = registry
        self.evaluator = evaluator or PolicyEvaluator()
        self._metrics = defaultdict(lambda: defaultdict(list))

    def choose_policy(self, policy_id: str, npc_id: str) -> Optional[Dict[str, Any]]:
        promoted = self.registry.get_promoted(policy_id)
        canary = self.registry.get_canary(policy_id)
        if canary and self._in_canary_cohort(npc_id, canary.get("canary_cohort_percent", 0.0)):
            return self._load_policy(canary)
        if promoted:
            return self._load_policy(promoted)
        if canary:
            return self._load_policy(canary)
        return None

    def decide_action(self, policy_id: str, npc_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        policy = self.choose_policy(policy_id, npc_id)
        if not policy:
            return {"action": "fallback_idle", "policy_version": None}

        ranked_actions = policy.get("model", {}).get("ranked_actions", [])
        action = ranked_actions[0] if ranked_actions else "fallback_idle"
        return {
            "action": action,
            "policy_version": policy.get("version"),
        }

    def record_metric(
        self,
        policy_id: str,
        policy_version: str,
        metric_name: str,
        value: float,
    ) -> None:
        key = f"{policy_id}@{policy_version}"
        self._metrics[key][metric_name].append(float(value))

    def evaluate_canary(self, policy_id: str, baseline_version: str, canary_version: str) -> Dict[str, Any]:
        baseline_metrics = self._summarize_metrics(policy_id, baseline_version)
        canary_metrics = self._summarize_metrics(policy_id, canary_version)

        result = self.evaluator.evaluate(baseline_metrics, canary_metrics)
        if result["passed"]:
            self.registry.promote(policy_id, canary_version)
            decision = "promoted"
        else:
            self.registry.rollback(policy_id, canary_version, "Regression gate failed")
            decision = "rolled_back"

        return {
            "decision": decision,
            "baseline": baseline_metrics,
            "canary": canary_metrics,
            "evaluation": result,
        }

    def _summarize_metrics(self, policy_id: str, version: str) -> Dict[str, float]:
        key = f"{policy_id}@{version}"
        metrics = self._metrics.get(key, {})
        summary: Dict[str, float] = {}
        for name, values in metrics.items():
            if values:
                summary[name] = sum(values) / len(values)
        return summary

    def _load_policy(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        artifact_path = Path(entry["artifact_path"])
        return json.loads(artifact_path.read_text(encoding="utf-8"))

    @staticmethod
    def _in_canary_cohort(npc_id: str, cohort_percent: float) -> bool:
        digest = hashlib.sha256(npc_id.encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % 100
        return bucket < int(cohort_percent)


__all__ = ["PolicyRuntimeAdapter"]
