from __future__ import annotations

from app.models import ExecutionPolicy


class PolicyDecision:
    def __init__(self, allowed: bool, reasons: list[str]) -> None:
        self.allowed = allowed
        self.reasons = reasons


def evaluate(policy: ExecutionPolicy) -> PolicyDecision:
    reasons: list[str] = []
    max_runtime = int(policy.resource_limits.get("max_runtime_seconds", 0))
    max_memory = str(policy.resource_limits.get("max_memory", ""))

    if max_runtime <= 0:
        reasons.append("max_runtime_seconds must be positive")
    if max_runtime > 7200:
        reasons.append("max_runtime_seconds exceeds upper bound")
    if not policy.tool_allowances:
        reasons.append("at least one tool allowance is required")
    if policy.network_scope not in {"internal", "internet"}:
        reasons.append("invalid network_scope")
    if not max_memory:
        reasons.append("max_memory is required")

    return PolicyDecision(allowed=len(reasons) == 0, reasons=reasons)

