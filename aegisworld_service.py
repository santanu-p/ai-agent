from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from aegisworld_models import (
    ExecutionPolicy,
    GoalSpec,
    SecurityIncident,
    new_id,
)
from aegisworld_runtime import AgentKernel, AgentMemory


DEFAULT_POLICY = ExecutionPolicy(
    tool_allowances=["planner", "executor"],
    resource_limits={"max_budget": 10.0, "max_latency_ms": 5000},
    network_scope="public_internet",
    data_scope="org_scoped",
    rollback_policy="auto_rollback_on_regression",
)


@dataclass
class Agent:
    agent_id: str
    name: str
    policy: ExecutionPolicy = field(default_factory=lambda: DEFAULT_POLICY)
    memory: AgentMemory = field(default_factory=AgentMemory)


class AegisWorldService:
    def __init__(self) -> None:
        self.kernel = AgentKernel()
        self.goals: Dict[str, GoalSpec] = {}
        self.agents: Dict[str, Agent] = {}
        self.traces: List[Dict[str, Any]] = []
        self.reflections: List[Dict[str, Any]] = []
        self.incidents: List[SecurityIncident] = []

    def create_goal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        goal = GoalSpec(
            goal_id=new_id("goal"),
            intent=payload["intent"],
            constraints=payload.get("constraints", {}),
            budget=float(payload.get("budget", 5.0)),
            deadline=payload.get("deadline", "unspecified"),
            risk_tolerance=payload.get("risk_tolerance", "medium"),
            domains=payload.get("domains", ["dev"]),
        )
        self.goals[goal.goal_id] = goal
        return goal.to_dict()

    def get_goal(self, goal_id: str) -> Dict[str, Any] | None:
        goal = self.goals.get(goal_id)
        return goal.to_dict() if goal else None

    def create_agent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        agent = Agent(agent_id=new_id("agent"), name=payload.get("name", "default-agent"))
        self.agents[agent.agent_id] = agent
        return {"agent_id": agent.agent_id, "name": agent.name}

    def execute(self, agent_id: str, goal_id: str) -> Dict[str, Any]:
        agent = self.agents[agent_id]
        goal = self.goals[goal_id]

        trace, reflection = self.kernel.execute_goal(
            agent_id=agent.agent_id,
            goal=goal,
            policy=agent.policy,
            memory=agent.memory,
        )

        self.traces.append(trace.to_dict())
        if reflection:
            self.reflections.append(reflection.to_dict())

        if trace.outcome.startswith("blocked:"):
            incident = SecurityIncident(
                incident_id=new_id("inc"),
                signal_set=["policy_gate_denied"],
                severity="medium",
                blast_radius="single_goal",
                auto_actions=["goal_quarantine", "policy_simulation_required"],
                verification_state="pending",
            )
            self.incidents.append(incident)

        return {
            "trace": trace.to_dict(),
            "reflection": reflection.to_dict() if reflection else None,
        }

    def get_memory(self, agent_id: str) -> Dict[str, Any]:
        memory = self.agents[agent_id].memory
        return {
            "episodic": memory.episodic,
            "session": memory.session,
            "semantic": memory.semantic,
        }

    def create_domain_project(self, domain: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        intent = payload.get("intent", f"Create {domain} project")
        goal = self.create_goal(
            {
                "intent": f"[{domain}] {intent}",
                "domains": [domain],
                "constraints": payload.get("constraints", {}),
                "budget": payload.get("budget", 5.0),
                "deadline": payload.get("deadline", "unspecified"),
                "risk_tolerance": payload.get("risk_tolerance", "medium"),
            }
        )
        return {"project_goal": goal}

    def list_incidents(self) -> List[Dict[str, Any]]:
        return [incident.to_dict() for incident in self.incidents]

    def simulate_policy(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        tool_allowances = payload.get("tool_allowances", ["planner", "executor"])
        policy = ExecutionPolicy(
            tool_allowances=tool_allowances,
            resource_limits=payload.get("resource_limits", {"max_budget": 10, "max_latency_ms": 5000}),
            network_scope=payload.get("network_scope", "public_internet"),
            data_scope=payload.get("data_scope", "org_scoped"),
            rollback_policy=payload.get("rollback_policy", "auto_rollback_on_regression"),
        )
        requested_tools = payload.get("requested_tools", ["planner"])
        estimated_cost = float(payload.get("estimated_cost", 1.0))
        estimated_latency_ms = int(payload.get("estimated_latency_ms", 1000))
        decision = self.kernel.policy_engine.evaluate(policy, requested_tools, estimated_cost, estimated_latency_ms)
        return decision.to_dict()
