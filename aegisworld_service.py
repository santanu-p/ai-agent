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


VALID_GOAL_STATES = {"created", "queued", "running", "completed", "blocked", "failed"}


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
        self.goal_status: Dict[str, str] = {}
        self.agents: Dict[str, Agent] = {}
        self.queue: List[Dict[str, str]] = []
        self.traces: List[Dict[str, Any]] = []
        self.reflections: List[Dict[str, Any]] = []
        self.incidents: List[SecurityIncident] = []
        self.changes: List[AutonomousChangeSet] = []

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
            self.goal_status[goal.goal_id] = "created"
            self._save_state()
            return goal.to_dict()

    def get_goal(self, goal_id: str) -> Dict[str, Any] | None:
        with self.lock:
            goal = self.goals.get(goal_id)
            if not goal:
                return None
            data = goal.to_dict()
            data["status"] = self.goal_status.get(goal_id, "created")
            return data

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
                "policy": self._policy_to_dict(agent.policy),
            }

    def update_agent_policy(self, agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            agent = self.agents[agent_id]
            merged_resource_limits = dict(agent.policy.resource_limits)
            merged_resource_limits.update(payload.get("resource_limits", {}))
            agent.policy = ExecutionPolicy(
                tool_allowances=payload.get("tool_allowances", agent.policy.tool_allowances),
                resource_limits=merged_resource_limits,
                network_scope=payload.get("network_scope", agent.policy.network_scope),
                data_scope=payload.get("data_scope", agent.policy.data_scope),
                rollback_policy=payload.get("rollback_policy", agent.policy.rollback_policy),
            )
            self._save_state()
            return {"agent_id": agent_id, "policy": self._policy_to_dict(agent.policy)}

    def execute(self, agent_id: str, goal_id: str) -> Dict[str, Any]:
        with self.lock:
            agent = self.agents[agent_id]
            goal = self.goals[goal_id]
            self.goal_status[goal_id] = "running"

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

            if trace.outcome.startswith("blocked:"):
                self.goal_status[goal_id] = "blocked"
                incident = SecurityIncident(
                    incident_id=new_id("inc"),
                    signal_set=["policy_gate_denied"],
                    severity="medium",
                    blast_radius="single_goal",
                    auto_actions=["goal_quarantine", "policy_simulation_required"],
                    verification_state="verified",
                )
                self.incidents.append(incident)
            else:
                self.goal_status[goal_id] = "completed"

            self._save_state()
            return {
                "trace": trace.to_dict(),
                "reflection": reflection.to_dict() if reflection else None,
                "goal_status": self.goal_status[goal_id],
            }

    def assign_goal(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            agent_id = payload["agent_id"]
            goal_id = payload["goal_id"]
            if agent_id not in self.agents:
                raise KeyError("agent_id")
            if goal_id not in self.goals:
                raise KeyError("goal_id")

            self.queue.append({"agent_id": agent_id, "goal_id": goal_id})
            self.goal_status[goal_id] = "queued"
            self._save_state()
            return {"queued": True, "queue_length": len(self.queue)}

    def run_scheduler(self, max_runs: int = 10) -> Dict[str, Any]:
        with self.lock:
            executed: List[Dict[str, Any]] = []
            while self.queue and len(executed) < max_runs:
                job = self.queue.pop(0)
                result = self.execute(job["agent_id"], job["goal_id"])
                executed.append(
                    {
                        "agent_id": job["agent_id"],
                        "goal_id": job["goal_id"],
                        "outcome": result["trace"]["outcome"],
                        "goal_status": result["goal_status"],
                    }
                )
            self._save_state()
            return {"executed": executed, "remaining_queue": len(self.queue)}

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

    def get_queue(self) -> List[Dict[str, str]]:
        with self.lock:
            return list(self.queue)

    def stats(self) -> Dict[str, Any]:
        with self.lock:
            total = len(self.traces)
            success = len([t for t in self.traces if t.get("outcome") == "success"])
            blocked = len([t for t in self.traces if str(t.get("outcome", "")).startswith("blocked:")])
            success_rate = (success / total) if total else 0.0
            return {
                "goals": len(self.goals),
                "agents": len(self.agents),
                "queue_length": len(self.queue),
                "executions_total": total,
                "executions_success": success,
                "executions_blocked": blocked,
                "success_rate": round(success_rate, 4),
                "incidents": len(self.incidents),
                "changes": len(self.changes),
            }

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

    def _policy_to_dict(self, policy: ExecutionPolicy) -> Dict[str, Any]:
        return {
            "tool_allowances": policy.tool_allowances,
            "resource_limits": policy.resource_limits,
            "network_scope": policy.network_scope,
            "data_scope": policy.data_scope,
            "rollback_policy": policy.rollback_policy,
        }

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "goals": [g.to_dict() for g in self.goals.values()],
            "goal_status": self.goal_status,
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "policy": self._policy_to_dict(a.policy),
                    "memory": {
                        "episodic": a.memory.episodic,
                        "session": a.memory.session,
                        "semantic": a.memory.semantic,
                    },
                }
                for a in self.agents.values()
            ],
            "queue": self.queue,
            "traces": self.traces,
            "reflections": self.reflections,
            "incidents": [i.to_dict() for i in self.incidents],
            "changes": [c.to_dict() for c in self.changes],
        }
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return

        data = json.loads(self.state_path.read_text(encoding="utf-8"))

        for g in data.get("goals", []):
            goal = GoalSpec(**g)
            self.goals[goal.goal_id] = goal

        self.goal_status = {
            goal_id: state
            for goal_id, state in data.get("goal_status", {}).items()
            if state in VALID_GOAL_STATES
        }

        for goal_id in self.goals:
            self.goal_status.setdefault(goal_id, "created")

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

        self.queue = data.get("queue", [])
        self.traces = data.get("traces", [])
        self.reflections = data.get("reflections", [])
        self.incidents = [SecurityIncident(**i) for i in data.get("incidents", [])]
        self.changes = [AutonomousChangeSet(**c) for c in data.get("changes", [])]
