from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from aegisworld_models import ExecutionPolicy


@dataclass
class PolicyDecision:
    allowed: bool
    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {"allowed": self.allowed, "reasons": self.reasons}


class PolicyEngine:
    """Machine-enforced policy checks used by runtime and SecOps loops."""

    def evaluate(
        self,
        policy: ExecutionPolicy,
        requested_tools: List[str],
        estimated_cost: float,
        estimated_latency_ms: int,
    ) -> PolicyDecision:
        reasons: List[str] = []

        max_budget = float(policy.resource_limits.get("max_budget", 0))
        if max_budget and estimated_cost > max_budget:
            reasons.append(f"budget_exceeded:{estimated_cost}>{max_budget}")

        max_latency = int(policy.resource_limits.get("max_latency_ms", 0))
        if max_latency and estimated_latency_ms > max_latency:
            reasons.append(f"latency_exceeded:{estimated_latency_ms}>{max_latency}")

        blocked = [tool for tool in requested_tools if not policy.allows_tool(tool)]
        if blocked:
            reasons.append(f"blocked_tools:{','.join(blocked)}")

        return PolicyDecision(allowed=not reasons, reasons=reasons)
