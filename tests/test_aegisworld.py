from pathlib import Path

from aegisworld_policy import PolicyEngine
from aegisworld_runtime import AgentKernel, AgentMemory
from aegisworld_models import ExecutionPolicy, GoalSpec
from aegisworld_service import AegisWorldService


def test_policy_blocks_unapproved_tool() -> None:
    policy = ExecutionPolicy(
        tool_allowances=["planner"],
        resource_limits={"max_budget": 5, "max_latency_ms": 1000},
        network_scope="public_internet",
        data_scope="org_scoped",
        rollback_policy="auto",
    )
    decision = PolicyEngine().evaluate(
        policy=policy,
        requested_tools=["executor"],
        estimated_cost=1.0,
        estimated_latency_ms=400,
    )
    assert decision.allowed is False
    assert any(r.startswith("blocked_tools") for r in decision.reasons)


def test_agent_kernel_updates_memory_on_success() -> None:
    kernel = AgentKernel()
    policy = ExecutionPolicy(
        tool_allowances=["planner", "executor"],
        resource_limits={"max_budget": 20, "max_latency_ms": 5000},
        network_scope="public_internet",
        data_scope="org_scoped",
        rollback_policy="auto",
    )
    goal = GoalSpec(
        goal_id="goal_1",
        intent="Ship a deployment",
        constraints={},
        budget=3.0,
        deadline="tomorrow",
        risk_tolerance="medium",
        domains=["dev"],
    )
    memory = AgentMemory()
    trace, reflection = kernel.execute_goal("agent_1", goal, policy, memory)

    assert trace.outcome == "success"
    assert reflection is not None
    assert memory.episodic
    assert f"goal:{goal.goal_id}" in memory.semantic


def test_service_workflow_end_to_end_and_learning(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    service = AegisWorldService(state_file=str(state_file))
    agent = service.create_agent({"name": "pilot-agent"})
    goal = service.create_goal({"intent": "Create CI pipeline", "domains": ["dev"]})

    response = service.execute(agent["agent_id"], goal["goal_id"])

    assert response["trace"]["outcome"] == "success"
    assert response["reflection"] is not None
    assert service.list_changes()
    summary = service.learning_summary()
    assert summary["total_reflections"] >= 1


def test_state_persistence_roundtrip(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    service = AegisWorldService(state_file=str(state_file))
    agent = service.create_agent({"name": "persist-agent"})
    goal = service.create_goal({"intent": "Persist me", "domains": ["dev"]})
    service.execute(agent["agent_id"], goal["goal_id"])

    reloaded = AegisWorldService(state_file=str(state_file))
    assert len(reloaded.agents) == 1
    assert len(reloaded.goals) == 1
    assert len(reloaded.list_traces()) == 1
