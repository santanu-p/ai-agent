from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.kernel import AgentKernel
from app.memory import TieredMemory
from app.models import ExecuteRequest, ExecutionPolicy, GoalSpec, RiskTolerance
from app.tool_registry import ToolRegistry


def _base_policy(tool_allowances: list[str]) -> ExecutionPolicy:
    return ExecutionPolicy(
        tool_allowances=tool_allowances,
        resource_limits={"max_cpu": "4", "max_memory": "8Gi", "max_runtime_seconds": 1200},
        network_scope="internet",
        data_scope="standard",
        rollback_policy="on_failure",
    )


def test_kernel_executes_success_path_with_adaptive_observations() -> None:
    kernel = AgentKernel(memory=TieredMemory(), tool_registry=ToolRegistry())
    request = ExecuteRequest(
        goal=GoalSpec(
            goal_id="g-1",
            intent="create and deploy service",
            constraints=[],
            budget=100,
            deadline=datetime.now(timezone.utc) + timedelta(days=1),
            risk_tolerance=RiskTolerance.medium,
            domains=["dev"],
        ),
        policy=_base_policy(["dev.pipeline", "ops.observe"]),
        context_snapshot={"cluster_health": "healthy"},
        governance_objectives=["deliver quickly"],
        governance_constraints=["no production downtime"],
        max_iterations=2,
    )
    response = kernel.execute(request)
    assert response.trace.outcome == "success"
    assert "dev.pipeline" in response.trace.tool_calls
    assert len(response.observations) == 2
    assert all(r.decision in {"continue", "stop"} for r in response.rationales)


def test_kernel_escalates_and_emits_policy_adjustment_on_repeated_failures() -> None:
    registry = ToolRegistry()
    registry._tools["dev.pipeline"] = lambda payload: f"failed to run pipeline: {payload}"  # type: ignore[attr-defined]
    kernel = AgentKernel(memory=TieredMemory(), tool_registry=registry)

    request = ExecuteRequest(
        goal=GoalSpec(
            goal_id="g-3",
            intent="deploy unstable service",
            constraints=[],
            budget=100,
            deadline=datetime.now(timezone.utc) + timedelta(days=1),
            risk_tolerance=RiskTolerance.high,
            domains=["dev"],
        ),
        policy=_base_policy(["dev.pipeline"]),
        context_snapshot={"last_deploy": "failed"},
        governance_objectives=["recover service"],
        governance_constraints=["preserve auditability"],
        max_iterations=3,
    )

    response = kernel.execute(request)

    assert response.trace.outcome == "failure"
    assert any(r.decision == "escalate" for r in response.rationales)
    assert response.policy_adjustment_suggestion is not None
    assert response.reflections


def test_kernel_generates_reflection_when_no_tools_available() -> None:
    kernel = AgentKernel(memory=TieredMemory(), tool_registry=ToolRegistry())
    request = ExecuteRequest(
        goal=GoalSpec(
            goal_id="g-2",
            intent="run social campaign",
            constraints=[],
            budget=50,
            deadline=datetime.now(timezone.utc) + timedelta(days=1),
            risk_tolerance=RiskTolerance.low,
            domains=["social"],
        ),
        policy=_base_policy(["unknown.tool"]),
        context_snapshot={"audience": "new"},
        governance_objectives=["brand safety"],
        governance_constraints=["no unreviewed copy"],
        max_iterations=1,
    )
    response = kernel.execute(request)
    assert response.trace.outcome == "failure"
    assert response.reflections
