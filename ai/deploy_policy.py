"""Deployment stage orchestration for policy rollout."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .policy_registry import PolicyRegistry


@dataclass(frozen=True)
class DeployResult:
    policy_id: str
    stage: str
    decision: str


class PolicyDeployer:
    """Runs deploy stage with canary then promotion/rollback."""

    def __init__(self, registry: PolicyRegistry) -> None:
        self.registry = registry

    def deploy_with_canary(
        self,
        policy_id: str,
        *,
        canary_percent: int,
        baseline_metrics: Dict[str, float],
        canary_metrics: Dict[str, float],
    ) -> DeployResult:
        self.registry.start_canary(policy_id, percent=canary_percent)
        decision = self.registry.evaluate_canary(policy_id, baseline_metrics, canary_metrics)
        return DeployResult(policy_id=policy_id, stage="deploy", decision=decision)
