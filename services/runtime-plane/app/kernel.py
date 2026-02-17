from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from app.memory import TieredMemory
from app.models import (
    ActionRationale,
    ExecuteRequest,
    ExecuteResponse,
    IterationObservation,
    PolicyAdjustmentSuggestion,
    ReflectionRecord,
    TaskTrace,
)
from app.tool_registry import ToolRegistry


class AgentKernel:
    def __init__(self, memory: TieredMemory, tool_registry: ToolRegistry) -> None:
        self._memory = memory
        self._tools = tool_registry

    def _plan(self, intent: str, domains: list[str], observation_delta: dict[str, object]) -> list[str]:
        steps = [f"analyze intent: {intent}", "decompose objective into tool tasks"]
        if observation_delta:
            steps.append(f"adapt plan using deltas: {sorted(observation_delta.keys())}")
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

    def _delta(self, previous: dict[str, object], current: dict[str, object]) -> dict[str, object]:
        delta: dict[str, object] = {}
        all_keys = set(previous) | set(current)
        for key in all_keys:
            if previous.get(key) != current.get(key):
                delta[key] = {"before": previous.get(key), "after": current.get(key)}
        return delta

    def execute(self, request: ExecuteRequest) -> ExecuteResponse:
        run_id = str(uuid4())
        trace_id = str(uuid4())
        start = perf_counter()

        steps: list[str] = []
        reflections: list[ReflectionRecord] = []
        rationales: list[ActionRationale] = []
        observations: list[IterationObservation] = list(request.iteration_observations)
        tool_calls: list[str] = []
        outcome = "success"

        self._memory.append_episodic(
            run_id,
            event=f"run started for goal {request.goal.goal_id}",
            cause="execute invoked",
            effect="initialized adaptive runtime loop",
            tags=["run-start"],
        )
        self._memory.append_session(
            request.goal.goal_id,
            event=f"intent={request.goal.intent}",
            cause="new goal received",
            effect="goal context attached to session memory",
            tags=["goal-context"],
        )

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
            rationales.append(
                ActionRationale(
                    iteration=0,
                    action="tool-selection",
                    decision="escalate",
                    reason="No allowed tools can execute the requested domains.",
                )
            )

        failure_streak = 0
        current_context = dict(request.context_snapshot)
        policy_adjustment_suggestion: PolicyAdjustmentSuggestion | None = None

        for idx in range(request.max_iterations):
            if outcome == "failure" and not selected_tools:
                break

            previous_context = dict(current_context)
            planning_steps = self._plan(request.goal.intent, request.goal.domains, observations[-1].delta if observations else {})
            iteration_step = f"iteration {idx + 1}: {' | '.join(planning_steps)}"
            steps.append(iteration_step)
            self._memory.append_episodic(
                run_id,
                event=iteration_step,
                cause="iteration start",
                effect="plan refreshed from latest observation delta",
                tags=["replan", f"iteration-{idx + 1}"],
            )

            results: list[str] = []
            for tool in selected_tools:
                result = self._tools.execute(tool, request.goal.intent)
                tool_calls.append(tool)
                results.append(result)

            has_failure_signal = any("fail" in result.lower() or "error" in result.lower() for result in results)
            failure_streak = failure_streak + 1 if has_failure_signal else 0
            status = "failure" if has_failure_signal else "success"

            current_context["last_status"] = status
            current_context["failure_streak"] = failure_streak
            delta = self._delta(previous_context, current_context)

            observation = IterationObservation(
                iteration=idx + 1,
                tool_results=results,
                delta=delta,
                status=status,
            )
            observations.append(observation)

            decision = "continue"
            reason = "Progressing normally."
            if failure_streak >= 2:
                decision = "escalate"
                reason = "Repeated failure signals detected across iterations."
                outcome = "failure"
            elif idx == request.max_iterations - 1:
                decision = "stop"
                reason = "Reached configured max iterations."

            rationales.append(
                ActionRationale(
                    iteration=idx + 1,
                    action="execute-tools",
                    decision=decision,
                    reason=reason,
                )
            )

            self._memory.append_episodic(
                run_id,
                event=f"iteration {idx + 1} decision={decision}",
                cause=f"observation status={status}",
                effect=reason,
                tags=[decision, f"iteration-{idx + 1}"],
            )

            if decision == "escalate":
                reflections.append(
                    ReflectionRecord(
                        reflection_id=str(uuid4()),
                        failure_class="repeated_execution_failures",
                        root_cause="tool outputs repeatedly signaled failure",
                        counterfactual="switch strategy or broaden allowed recovery tools",
                        policy_patch="allow fallback diagnostic/remediation tools",
                        memory_patch="record repeated-failure pattern for policy review",
                    )
                )
                policy_adjustment_suggestion = PolicyAdjustmentSuggestion(
                    title="Norm proposal: adaptive fallback allowance",
                    trigger="Two consecutive failing observations.",
                    recommendation=(
                        "Adjust governance constraints to permit one diagnostic fallback tool "
                        "after consecutive failures while preserving current data/network scopes."
                    ),
                )
                break

            if decision == "stop":
                break

        elapsed = perf_counter() - start
        latency_ms = int(elapsed * 1000)
        token_cost = round(1.2 + len(steps) * 0.05 + len(tool_calls) * 0.02, 4)

        if outcome == "success":
            self._memory.append_semantic(
                "successful_patterns",
                event=f"goal={request.goal.goal_id}",
                cause="execution completed without escalation",
                effect="pattern available for future routing",
                tags=["success"],
            )
        else:
            self._memory.append_semantic(
                "failure_patterns",
                event=f"goal={request.goal.goal_id}",
                cause="execution escalated or lacked tools",
                effect="pattern available for policy adjustment",
                tags=["failure", "policy-review"],
            )

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
            observations=observations,
            rationales=rationales,
            policy_adjustment_suggestion=policy_adjustment_suggestion,
            memory_entries=self._memory.snapshot(
                run_id=run_id,
                goal_id=request.goal.goal_id,
                topic="successful_patterns" if outcome == "success" else "failure_patterns",
            ),
        )
