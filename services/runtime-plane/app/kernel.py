from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from app.memory import TieredMemory
from app.models import ExecuteRequest, ExecuteResponse, ReflectionRecord, TaskTrace
from app.tool_registry import ToolRegistry


class AgentKernel:
    def __init__(self, memory: TieredMemory, tool_registry: ToolRegistry) -> None:
        self._memory = memory
        self._tools = tool_registry

    def _plan(self, intent: str, domains: list[str]) -> list[str]:
        steps = [f"analyze intent: {intent}", "decompose objective into tool tasks"]
        if "social" in domains:
            steps.append("prepare social tool payload")
        if "dev" in domains:
            steps.append("prepare dev pipeline payload")
        if "games" in domains:
            steps.append("prepare game simulation payload")
        return steps

    def _select_tools(self, domains: list[str], allowances: list[str]) -> list[str]:
        candidates = []
        if "social" in domains:
            candidates.append("social.publish")
        if "dev" in domains:
            candidates.append("dev.pipeline")
        if "games" in domains:
            candidates.append("games.simulate")
        candidates.append("ops.observe")

        return [tool for tool in candidates if tool in allowances and self._tools.has_tool(tool)]

    def execute(self, request: ExecuteRequest) -> ExecuteResponse:
        run_id = str(uuid4())
        trace_id = str(uuid4())
        start = perf_counter()

        steps = self._plan(request.goal.intent, request.goal.domains)
        reflections: list[ReflectionRecord] = []
        tool_calls: list[str] = []
        outcome = "success"

        self._memory.append_episodic(run_id, f"run started for goal {request.goal.goal_id}")
        self._memory.append_session(request.goal.goal_id, f"intent={request.goal.intent}")

        selected_tools = self._select_tools(request.goal.domains, request.policy.tool_allowances)
        if not selected_tools:
            outcome = "failure"
            reflections.append(
                ReflectionRecord(
                    reflection_id=str(uuid4()),
                    failure_class="no_tool_selected",
                    root_cause="policy tool allowances excluded all domain tools",
                    counterfactual="include at least one tool per active domain",
                    policy_patch="add domain-compatible tool allowances",
                    memory_patch="store policy misconfiguration exemplar",
                )
            )

        for idx in range(request.max_iterations):
            step_name = f"iteration {idx + 1}: execute and observe"
            steps.append(step_name)
            self._memory.append_episodic(run_id, step_name)
            for tool in selected_tools:
                result = self._tools.execute(tool, request.goal.intent)
                tool_calls.append(tool)
                self._memory.append_episodic(run_id, result)

        elapsed = perf_counter() - start
        latency_ms = int(elapsed * 1000)
        token_cost = round(1.2 + len(steps) * 0.05 + len(tool_calls) * 0.02, 4)

        if outcome == "success":
            self._memory.append_semantic("successful_patterns", f"goal={request.goal.goal_id}")
        else:
            self._memory.append_semantic("failure_patterns", f"goal={request.goal.goal_id}")

        trace = TaskTrace(
            trace_id=trace_id,
            goal_id=request.goal.goal_id,
            steps=steps,
            tool_calls=tool_calls,
            model_calls=["router:general-purpose"],
            latency_ms=latency_ms,
            token_cost=token_cost,
            outcome=outcome,
        )

        return ExecuteResponse(
            trace=trace,
            reflections=reflections,
            memory_entries=self._memory.snapshot(
                run_id=run_id,
                goal_id=request.goal.goal_id,
                topic="successful_patterns" if outcome == "success" else "failure_patterns",
            ),
        )

