from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List

from aegisworld_learning import LearningEngine
from aegisworld_models import (
    AutonomousChangeSet,
    ExecutionPolicy,
    GoalSpec,
    SecurityIncident,
    new_id,
)
from aegisworld_runtime import AgentKernel, AgentMemory


def default_policy() -> ExecutionPolicy:
    return ExecutionPolicy(
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
    policy: ExecutionPolicy = field(default_factory=default_policy)
    memory: AgentMemory = field(default_factory=AgentMemory)


class AegisWorldService:
    def __init__(self, state_file: str = "state/aegisworld_state.json") -> None:
        self.kernel = AgentKernel()
        self.learning = LearningEngine()
        self.lock = RLock()
        self.state_path = Path(state_file)

        self.goals: Dict[str, GoalSpec] = {}
        self.agents: Dict[str, Agent] = {}
        self.traces: List[Dict[str, Any]] = []
        self.reflections: List[Dict[str, Any]] = []
        self.incidents: List[SecurityIncident] = []
        self.changes: List[AutonomousChangeSet] = []
        self.cost_ledger: Dict[str, float] = {}

        self._load_state()

    def create_goal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
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
            self._save_state()
            return goal.to_dict()

    def get_goal(self, goal_id: str) -> Dict[str, Any] | None:
        with self.lock:
            goal = self.goals.get(goal_id)
            return goal.to_dict() if goal else None

    def create_agent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            agent = Agent(agent_id=new_id("agent"), name=payload.get("name", "default-agent"))
            self.agents[agent.agent_id] = agent
            self.cost_ledger.setdefault(agent.agent_id, 0.0)
            self._save_state()
            return {"agent_id": agent.agent_id, "name": agent.name}

    def get_agent(self, agent_id: str) -> Dict[str, Any] | None:
        with self.lock:
            agent = self.agents.get(agent_id)
            if not agent:
                return None
            return {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "cost_spend": self.cost_ledger.get(agent.agent_id, 0.0),
                "policy": {
                    "tool_allowances": agent.policy.tool_allowances,
                    "resource_limits": agent.policy.resource_limits,
                    "network_scope": agent.policy.network_scope,
                    "data_scope": agent.policy.data_scope,
                    "rollback_policy": agent.policy.rollback_policy,
                },
            }

    def update_agent_policy(self, agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            agent = self.agents[agent_id]
            updated = ExecutionPolicy(
                tool_allowances=payload.get("tool_allowances", agent.policy.tool_allowances),
                resource_limits=payload.get("resource_limits", agent.policy.resource_limits),
                network_scope=payload.get("network_scope", agent.policy.network_scope),
                data_scope=payload.get("data_scope", agent.policy.data_scope),
                rollback_policy=payload.get("rollback_policy", agent.policy.rollback_policy),
            )
            agent.policy = updated
            self._save_state()
            return self.get_agent(agent_id) or {}

    def execute(self, agent_id: str, goal_id: str) -> Dict[str, Any]:
        with self.lock:
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
                reflection_dict = reflection.to_dict()
                self.reflections.append(reflection_dict)
                self._propose_change(reflection_dict)

            self._update_costs(agent.agent_id, trace)

            if trace.outcome.startswith("blocked:"):
                incident = SecurityIncident(
                    incident_id=new_id("inc"),
                    signal_set=["policy_gate_denied"],
                    severity="medium",
                    blast_radius="single_goal",
                    auto_actions=["goal_quarantine", "policy_simulation_required"],
                    verification_state="verified",
                )
                self.incidents.append(incident)

            self._save_state()
            return {
                "trace": trace.to_dict(),
                "reflection": reflection.to_dict() if reflection else None,
            }

    def _update_costs(self, agent_id: str, trace: Any) -> None:
        token_cost = float(getattr(trace, "token_cost", 0))
        estimated_dollars = token_cost * 0.00001
        self.cost_ledger[agent_id] = self.cost_ledger.get(agent_id, 0.0) + estimated_dollars

    def get_memory(self, agent_id: str) -> Dict[str, Any]:
        with self.lock:
            memory = self.agents[agent_id].memory
            return {
                "episodic": memory.episodic,
                "session": memory.session,
                "semantic": memory.semantic,
            }

    def create_domain_project(self, domain: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        intent = payload.get("intent", f"Create {domain} project")
        return {
            "project_goal": self.create_goal(
                {
                    "intent": f"[{domain}] {intent}",
                    "domains": [domain],
                    "constraints": payload.get("constraints", {}),
                    "budget": payload.get("budget", 5.0),
                    "deadline": payload.get("deadline", "unspecified"),
                    "risk_tolerance": payload.get("risk_tolerance", "medium"),
                }
            )
        }

    def list_incidents(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [incident.to_dict() for incident in self.incidents]

    def list_traces(self) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.traces)

    def list_reflections(self) -> List[Dict[str, Any]]:
        with self.lock:
            return list(self.reflections)

    def list_changes(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [c.to_dict() for c in self.changes]

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

    def learning_summary(self) -> Dict[str, Any]:
        with self.lock:
            return self.learning.summarize_reflections(self.reflections).to_dict()

    def compact_memory(self, agent_id: str, max_items: int = 100) -> Dict[str, Any]:
        with self.lock:
            agent = self.agents[agent_id]
            before = len(agent.memory.semantic)
            agent.memory.semantic = self.learning.compact_semantic_memory(agent.memory.semantic, max_items=max_items)
            after = len(agent.memory.semantic)
            self._save_state()
            return {"agent_id": agent_id, "semantic_before": before, "semantic_after": after}

    def metrics(self) -> Dict[str, Any]:
        with self.lock:
            total_runs = len(self.traces)
            success_runs = len([t for t in self.traces if t.get("outcome") == "success"])
            success_rate = (success_runs / total_runs) if total_runs else 0.0
            total_estimated_cost = sum(self.cost_ledger.values())
            return {
                "goals": len(self.goals),
                "agents": len(self.agents),
                "traces": total_runs,
                "success_rate": success_rate,
                "incidents": len(self.incidents),
                "reflections": len(self.reflections),
                "changes": len(self.changes),
                "estimated_cost_usd": round(total_estimated_cost, 6),
            }

    def _propose_change(self, reflection: Dict[str, Any]) -> None:
        patch = reflection.get("policy_patch") or {}
        change = AutonomousChangeSet(
            change_id=new_id("chg"),
            target="execution_policy",
            diff=patch,
            risk_score=0.2 if reflection.get("failure_class") == "none" else 0.6,
            canary_result="pass" if reflection.get("failure_class") == "none" else "pending",
            promotion_state="candidate",
        )
        self.changes.append(change)

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "goals": [g.to_dict() for g in self.goals.values()],
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "policy": {
                        "tool_allowances": a.policy.tool_allowances,
                        "resource_limits": a.policy.resource_limits,
                        "network_scope": a.policy.network_scope,
                        "data_scope": a.policy.data_scope,
                        "rollback_policy": a.policy.rollback_policy,
                    },
                    "memory": {
                        "episodic": a.memory.episodic,
                        "session": a.memory.session,
                        "semantic": a.memory.semantic,
                    },
                }
                for a in self.agents.values()
            ],
            "traces": self.traces,
            "reflections": self.reflections,
            "incidents": [i.to_dict() for i in self.incidents],
            "changes": [c.to_dict() for c in self.changes],
            "cost_ledger": self.cost_ledger,
        }
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return

        data = json.loads(self.state_path.read_text(encoding="utf-8"))

        for g in data.get("goals", []):
            goal = GoalSpec(**g)
            self.goals[goal.goal_id] = goal

        for a in data.get("agents", []):
            policy_data = a.get("policy", {})
            policy = ExecutionPolicy(**policy_data)
            memory_data = a.get("memory", {})
            memory = AgentMemory(
                episodic=memory_data.get("episodic", []),
                session=memory_data.get("session", {}),
                semantic=memory_data.get("semantic", {}),
            )
            agent = Agent(agent_id=a["agent_id"], name=a["name"], policy=policy, memory=memory)
            self.agents[agent.agent_id] = agent

        self.traces = data.get("traces", [])
        self.reflections = data.get("reflections", [])
        self.incidents = [SecurityIncident(**i) for i in data.get("incidents", [])]
        self.changes = [AutonomousChangeSet(**c) for c in data.get("changes", [])]
        self.cost_ledger = data.get("cost_ledger", {})
