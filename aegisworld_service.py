from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List

from aegisworld_benchmark import BenchmarkRunner
from aegisworld_learning import LearningEngine
from aegisworld_models import (
    AutonomousChangeSet,
    ExecutionPolicy,
    GoalSpec,
    SecurityIncident,
    new_id,
)
from aegisworld_runtime import AgentKernel, AgentMemory


MONTHLY_COST_LIMIT = 150000.0


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
    spent_budget: float = 0.0
    goal_spend: Dict[str, float] = field(default_factory=dict)


class AegisWorldService:
    def __init__(self, state_file: str = "state/aegisworld_state.json") -> None:
        self.kernel = AgentKernel()
        self.learning = LearningEngine()
        self.benchmark = BenchmarkRunner()
        self.lock = RLock()
        self.state_path = Path(state_file)

        self.goals: Dict[str, GoalSpec] = {}
        self.agents: Dict[str, Agent] = {}
        self.traces: List[Dict[str, Any]] = []
        self.reflections: List[Dict[str, Any]] = []
        self.incidents: List[SecurityIncident] = []
        self.changes: List[AutonomousChangeSet] = []
        self.total_spend: float = 0.0

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
                "spent_budget": agent.spent_budget,
                "goal_spend": dict(agent.goal_spend),
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
            policy = ExecutionPolicy(
                tool_allowances=payload.get("tool_allowances", agent.policy.tool_allowances),
                resource_limits=payload.get("resource_limits", agent.policy.resource_limits),
                network_scope=payload.get("network_scope", agent.policy.network_scope),
                data_scope=payload.get("data_scope", agent.policy.data_scope),
                rollback_policy=payload.get("rollback_policy", agent.policy.rollback_policy),
            )
            agent.policy = policy
            self._save_state()
            return self.get_agent(agent_id) or {}

    def execute(self, agent_id: str, goal_id: str) -> Dict[str, Any]:
        with self.lock:
            agent = self.agents[agent_id]
            goal = self.goals[goal_id]

            goal_spend = float(agent.goal_spend.get(goal.goal_id, 0.0))
            if goal_spend >= goal.budget:
                trace = {
                    "trace_id": new_id("trace"),
                    "goal_id": goal.goal_id,
                    "agent_id": agent.agent_id,
                    "steps": ["budget_guard"],
                    "tool_calls": [],
                    "model_calls": [],
                    "latency_ms": 5,
                    "token_cost": 0,
                    "outcome": "blocked:goal_budget_exhausted",
                }
                self.traces.append(trace)
                self._raise_incident("budget_guard_triggered", "high", "single_goal")
                self._save_state()
                return {"trace": trace, "reflection": None}

            estimated_run_cost = self.kernel.estimate_run_cost(goal)
            if goal_spend + estimated_run_cost > goal.budget:
                trace = {
                    "trace_id": new_id("trace"),
                    "goal_id": goal.goal_id,
                    "agent_id": agent.agent_id,
                    "steps": ["budget_guard_precheck"],
                    "tool_calls": [],
                    "model_calls": [],
                    "latency_ms": 5,
                    "token_cost": 0,
                    "outcome": "blocked:goal_budget_precheck",
                }
                self.traces.append(trace)
                self._raise_incident("budget_guard_precheck_triggered", "high", "single_goal")
                self._save_state()
                return {"trace": trace, "reflection": None}

            if self.total_spend >= MONTHLY_COST_LIMIT:
                trace = {
                    "trace_id": new_id("trace"),
                    "goal_id": goal.goal_id,
                    "agent_id": agent.agent_id,
                    "steps": ["monthly_budget_guard"],
                    "tool_calls": [],
                    "model_calls": [],
                    "latency_ms": 5,
                    "token_cost": 0,
                    "outcome": "blocked:monthly_budget_exhausted",
                }
                self.traces.append(trace)
                self._raise_incident("monthly_budget_guard_triggered", "critical", "platform")
                self._save_state()
                return {"trace": trace, "reflection": None}

            trace, reflection = self.kernel.execute_goal(
                agent_id=agent.agent_id,
                goal=goal,
                policy=agent.policy,
                memory=agent.memory,
            )

            trace_dict = trace.to_dict()
            self.traces.append(trace_dict)
            run_cost = float(trace.token_cost) / 100.0
            agent.spent_budget += run_cost
            agent.goal_spend[goal.goal_id] = float(agent.goal_spend.get(goal.goal_id, 0.0)) + run_cost
            self.total_spend += run_cost

            if reflection:
                reflection_dict = reflection.to_dict()
                self.reflections.append(reflection_dict)
                self._propose_change(reflection_dict)

            if trace.outcome.startswith("blocked:"):
                self._raise_incident("policy_gate_denied", "medium", "single_goal")

            self._save_state()
            return {
                "trace": trace_dict,
                "reflection": reflection.to_dict() if reflection else None,
            }

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
            benchmark = self.benchmark.summarize_traces(self.traces).to_dict()
            availability = 1.0 if benchmark["total_runs"] == 0 else benchmark["success_rate"]
            return {
                "total_agents": len(self.agents),
                "total_goals": len(self.goals),
                "total_spend": round(self.total_spend, 2),
                "monthly_cost_limit": MONTHLY_COST_LIMIT,
                "availability_estimate": availability,
                "benchmark": benchmark,
                "incident_count": len(self.incidents),
            }

    def benchmark_run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            agent_id = payload["agent_id"]
            goal_ids = payload.get("goal_ids", [])
            for gid in goal_ids:
                if gid in self.goals and agent_id in self.agents:
                    self.execute(agent_id, gid)
            return self.benchmark.summarize_traces(self.traces).to_dict()

    def _raise_incident(self, signal: str, severity: str, blast_radius: str) -> None:
        incident = SecurityIncident(
            incident_id=new_id("inc"),
            signal_set=[signal],
            severity=severity,
            blast_radius=blast_radius,
            auto_actions=["quarantine", "policy_simulation_required"],
            verification_state="verified",
        )
        self.incidents.append(incident)

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
                    "spent_budget": a.spent_budget,
                    "goal_spend": a.goal_spend,
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
            "total_spend": self.total_spend,
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
            agent = Agent(
                agent_id=a["agent_id"],
                name=a["name"],
                policy=policy,
                memory=memory,
                spent_budget=float(a.get("spent_budget", 0.0)),
                goal_spend={
                    goal_id: float(amount)
                    for goal_id, amount in (a.get("goal_spend", {}) or {}).items()
                },
            )
            self.agents[agent.agent_id] = agent

        self.traces = data.get("traces", [])
        self.reflections = data.get("reflections", [])
        self.incidents = [SecurityIncident(**i) for i in data.get("incidents", [])]
        self.changes = [AutonomousChangeSet(**c) for c in data.get("changes", [])]
        self.total_spend = float(data.get("total_spend", 0.0))
