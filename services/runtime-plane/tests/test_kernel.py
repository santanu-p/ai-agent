from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.kernel import AgentKernel
from app.memory import TieredMemory
from app.models import ExecuteRequest, ExecutionPolicy, GoalSpec, RiskTolerance
from app.tool_registry import ToolRegistry


def test_kernel_executes_success_path() -> None:
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
        policy=ExecutionPolicy(
            tool_allowances=["dev.pipeline", "ops.observe"],
            resource_limits={"max_cpu": "4", "max_memory": "8Gi", "max_runtime_seconds": 1200},
            network_scope="internet",
            data_scope="standard",
            rollback_policy="on_failure",
        ),
        max_iterations=2,
    )
    response = kernel.execute(request)
    assert response.trace.outcome == "success"
    assert "dev.pipeline" in response.trace.tool_calls


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
        policy=ExecutionPolicy(
            tool_allowances=["unknown.tool"],
            resource_limits={"max_cpu": "4", "max_memory": "8Gi", "max_runtime_seconds": 1200},
            network_scope="internet",
            data_scope="standard",
            rollback_policy="on_failure",
        ),
        max_iterations=1,
    )
    response = kernel.execute(request)
    assert response.trace.outcome == "failure"
    assert response.reflections

