from __future__ import annotations

from app.engine import cluster_failures, evaluate_patch, synthesize_reflection
from app.models import EvaluatePatchRequest, ReflectionRequest, TaskTrace


def test_cluster_failures_groups_by_class() -> None:
    result = cluster_failures(
        [
            "tool not found during execute",
            "policy deny for high-risk network scope",
            "latency timeout in planning stage",
        ]
    )
    assert "tool_resolution_failure" in result.clusters
    assert "policy_denial" in result.clusters


def test_reflection_synthesis_returns_patch_hints() -> None:
    reflection = synthesize_reflection(
        ReflectionRequest(
            trace=TaskTrace(
                trace_id="t-1",
                goal_id="g-1",
                steps=["start", "error: tool not found"],
                tool_calls=[],
                model_calls=[],
                latency_ms=1800,
                token_cost=1.2,
                outcome="failure",
            )
        )
    )
    assert reflection.policy_patch
    assert reflection.memory_patch


def test_patch_evaluation_rejects_regression() -> None:
    response = evaluate_patch(
        EvaluatePatchRequest(
            baseline_score=0.82,
            candidate_score=0.79,
            observed_p95_latency_ms=12000,
            error_budget_remaining=0.5,
        )
    )
    assert response.recommendation == "reject"

