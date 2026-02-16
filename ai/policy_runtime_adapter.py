"""Runtime policy loading and safe NPC decision integration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .policy_registry import PolicyRegistry


class PolicyRuntimeAdapter:
    """Loads promoted policies and applies canary routing for NPC decisions."""

    def __init__(self, registry: PolicyRegistry, fallback_policy: str = "rule_based_v1") -> None:
        self.registry = registry
        self.fallback_policy = fallback_policy

    def select_policy_for_npc(self, npc_id: str) -> str:
        """Return the policy artifact path or fallback name for this NPC."""
        active = self.registry.get_active_policy()
        if active:
            return str(active["artifact_path"])

        canary = self._find_canary_policy()
        if canary and self._in_canary_cohort(npc_id, int(canary.get("canary_percent", 0))):
            return str(canary["artifact_path"])

        return self.fallback_policy

    def decide(self, npc_id: str, observation: Mapping[str, Any]) -> Dict[str, Any]:
        """Invoke selected policy with a strict-safe fallback on errors."""
        selected = self.select_policy_for_npc(npc_id)
        if selected == self.fallback_policy:
            return {"policy": selected, "action": "hold"}

        try:
            action = self._infer_with_artifact(Path(selected), observation)
            return {"policy": selected, "action": action}
        except Exception:
            return {"policy": self.fallback_policy, "action": "hold", "degraded": True}

    def _find_canary_policy(self) -> Optional[Dict[str, Any]]:
        for record in self.registry.list_policies():
            if record.get("rollout_status") == "canary":
                return record
        return None

    def _in_canary_cohort(self, npc_id: str, percent: int) -> bool:
        if percent <= 0:
            return False
        digest = hashlib.sha256(npc_id.encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % 100
        return bucket < percent

    def _infer_with_artifact(self, artifact_path: Path, observation: Mapping[str, Any]) -> str:
        """Placeholder inference using artifact metadata.

        Real environments should replace this with model loading + runtime inference.
        """
        with artifact_path.open("r", encoding="utf-8") as fh:
            artifact = json.load(fh)
        score = float(artifact.get("metrics", {}).get("combined_score", 0.0))
        threat = float(observation.get("threat_level", 0.0))
        if score > 0.6 and threat > 0.7:
            return "engage"
        if threat < 0.2:
            return "patrol"
        return "hold"
