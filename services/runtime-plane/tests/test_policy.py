from __future__ import annotations

from app.models import ExecutionPolicy
from app.policy import evaluate


def test_policy_denies_excess_runtime() -> None:
    decision = evaluate(
        ExecutionPolicy(
            tool_allowances=["dev.pipeline"],
            resource_limits={"max_cpu": "4", "max_memory": "8Gi", "max_runtime_seconds": 8000},
            network_scope="internet",
            data_scope="standard",
            rollback_policy="on_failure",
        )
    )
    assert not decision.allowed
    assert "exceeds upper bound" in " ".join(decision.reasons)


def test_policy_accepts_valid_request() -> None:
    decision = evaluate(
        ExecutionPolicy(
            tool_allowances=["dev.pipeline"],
            resource_limits={"max_cpu": "4", "max_memory": "8Gi", "max_runtime_seconds": 1200},
            network_scope="internet",
            data_scope="standard",
            rollback_policy="on_failure",
        )
    )
    assert decision.allowed

