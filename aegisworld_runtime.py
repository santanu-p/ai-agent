from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Dict, List

from aegisworld_models import (
    ExecutionPolicy,
    GoalSpec,
    ReflectionRecord,
    TaskTrace,
    new_id,
)
from aegisworld_policy import PolicyDecision, PolicyEngine


@dataclass
class AgentMemory:
    episodic: List[Dict[str, Any]] = field(default_factory=list)
    session: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    semantic: Dict[str, str] = field(default_factory=dict)


@dataclass
class AgentRuntimeState:
    consecutive_failures: int = 0
    circuit_open: bool = False


class AgentKernel:
    """Implements Plan → Execute → Observe → Reflect → Patch Memory/Policy → Re-plan."""

    def __init__(self, policy_engine: PolicyEngine | None = None) -> None:
        self.policy_engine = policy_engine or PolicyEngine()
        self.max_retries = 2
        self.circuit_breaker_threshold = 3

    def execute_goal(
        self,
        agent_id: str,
        goal: GoalSpec,
        policy: ExecutionPolicy,
        memory: AgentMemory,
        runtime_state: AgentRuntimeState | None = None,
    ) -> tuple[TaskTrace, ReflectionRecord | None]:
        state = runtime_state or AgentRuntimeState()

        if state.circuit_open:
            decision = PolicyDecision(allowed=False, reasons=["local_circuit_open"])
            return self._blocked_trace(agent_id, goal, ["circuit_guard"], decision), self._reflect_failure(goal, decision)

        start = perf_counter()
        plan = self._plan(goal)
        estimate = self._estimate(plan)

        decision = self.policy_engine.evaluate(
            policy=policy,
            requested_tools=estimate["tools"],
            estimated_cost=estimate["cost"],
            estimated_latency_ms=estimate["latency_ms"],
            requested_network_scope=estimate["network_scope"],
            requested_data_scope=estimate["data_scope"],
        )

        if not decision.allowed:
            state.consecutive_failures += 1
            if state.consecutive_failures >= self.circuit_breaker_threshold:
                state.circuit_open = True
            return self._blocked_trace(agent_id, goal, plan, decision), self._reflect_failure(goal, decision)

        results = self._execute_with_retries(plan)
        if results["status"] != "ok":
            state.consecutive_failures += 1
            if state.consecutive_failures >= self.circuit_breaker_threshold:
                state.circuit_open = True
            failure_decision = PolicyDecision(allowed=False, reasons=["execution_failed_after_retries"])
            return self._blocked_trace(agent_id, goal, plan, failure_decision), self._reflect_failure(goal, failure_decision)

        state.consecutive_failures = 0
        state.circuit_open = False

        observation = self._observe(results)
        reflection = self._reflect_success(goal, observation)
        self._patch_memory(memory, goal.goal_id, observation, reflection)

        latency_ms = int((perf_counter() - start) * 1000)
        trace = TaskTrace(
            trace_id=new_id("trace"),
            goal_id=goal.goal_id,
            agent_id=agent_id,
            steps=[*plan, "observe", "reflect", "patch_memory_policy", "replan_ready"],
            tool_calls=results["tool_calls"],
            model_calls=results["model_calls"],
            latency_ms=max(latency_ms, results["latency_ms"]),
            token_cost=results["token_cost"],
            outcome="success",
        )
        return trace, reflection

    def _plan(self, goal: GoalSpec) -> List[str]:
        return [
            f"decompose_goal:{goal.intent}",
            "select_tools",
            "execute_tasks",
        ]

    def _estimate(self, plan: List[str]) -> Dict[str, Any]:
        tool_count = 2 if "select_tools" in plan else 1
        return {
            "tools": ["planner", "executor"][:tool_count],
            "cost": 2.5,
            "latency_ms": 1200,
            "network_scope": "public_internet",
            "data_scope": "org_scoped",
        }

    def _execute_with_retries(self, plan: List[str]) -> Dict[str, Any]:
        for attempt in range(1, self.max_retries + 2):
            result = self._execute(plan, attempt)
            if result["status"] == "ok":
                return result
        return {
            "status": "failed",
            "tool_calls": [{"tool": "executor", "status": "failed"}],
            "model_calls": [],
            "latency_ms": 0,
            "token_cost": 0,
        }

    def _execute(self, plan: List[str], attempt: int) -> Dict[str, Any]:
        return {
            "status": "ok",
            "tool_calls": [
                {"tool": "planner", "status": "ok", "attempt": attempt},
                {"tool": "executor", "status": "ok", "attempt": attempt},
            ],
            "model_calls": [{"model": "router/default", "tokens": 420, "status": "ok"}],
            "latency_ms": 1400,
            "token_cost": 420,
        }

    def _observe(self, results: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "tool_success_rate": 1.0,
            "model_success_rate": 1.0,
            "latency_ms": results["latency_ms"],
            "token_cost": results["token_cost"],
        }

    def _reflect_success(self, goal: GoalSpec, observation: Dict[str, Any]) -> ReflectionRecord:
        return ReflectionRecord(
            record_id=new_id("refl"),
            goal_id=goal.goal_id,
            failure_class="none",
            root_cause="n/a",
            counterfactual="n/a",
            policy_patch={"hint": "increase_parallelism_if_cost_allows"},
            memory_patch={"pattern": f"Successful intent: {goal.intent}"},
        )

    def _reflect_failure(self, goal: GoalSpec, decision: PolicyDecision) -> ReflectionRecord:
        return ReflectionRecord(
            record_id=new_id("refl"),
            goal_id=goal.goal_id,
            failure_class="policy_violation",
            root_cause="policy gate denied execution",
            counterfactual="adjust tool set or lower budget/latency",
            policy_patch={"reasons": decision.reasons},
            memory_patch={"avoid": "blocked combination"},
        )

    def _patch_memory(
        self,
        memory: AgentMemory,
        goal_id: str,
        observation: Dict[str, Any],
        reflection: ReflectionRecord,
    ) -> None:
        memory.episodic.append({"goal_id": goal_id, "observation": observation})
        memory.session.setdefault(goal_id, []).append(reflection.to_dict())
        memory.semantic[f"goal:{goal_id}"] = reflection.memory_patch.get("pattern", "")

    def _blocked_trace(
        self,
        agent_id: str,
        goal: GoalSpec,
        plan: List[str],
        decision: PolicyDecision,
    ) -> TaskTrace:
        return TaskTrace(
            trace_id=new_id("trace"),
            goal_id=goal.goal_id,
            agent_id=agent_id,
            steps=[*plan, "policy_denied"],
            tool_calls=[],
            model_calls=[],
            latency_ms=20,
            token_cost=0,
            outcome=f"blocked:{'|'.join(decision.reasons)}",
        )
