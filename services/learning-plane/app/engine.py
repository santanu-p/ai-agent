from __future__ import annotations

from collections import defaultdict
from uuid import uuid4

from app.models import (
    ClusterResult,
    EvaluatePatchRequest,
    EvaluatePatchResponse,
    ReflectionRecord,
    ReflectionRequest,
)


def classify_failure(step_text: str) -> str:
    text = step_text.lower()
    if "tool" in text and "not found" in text:
        return "tool_resolution_failure"
    if "timeout" in text or "latency" in text:
        return "latency_budget_exceeded"
    if "policy" in text and "deny" in text:
        return "policy_denial"
    return "unknown_failure"


def cluster_failures(step_strings: list[str]) -> ClusterResult:
    clusters: dict[str, list[str]] = defaultdict(list)
    for step in step_strings:
        cluster = classify_failure(step)
        clusters[cluster].append(step)
    return ClusterResult(clusters=dict(clusters))


def synthesize_reflection(request: ReflectionRequest) -> ReflectionRecord:
    failure_steps = [s for s in request.trace.steps if "fail" in s.lower() or "error" in s.lower()]
    representative = failure_steps[0] if failure_steps else "no explicit failure step found"
    failure_class = classify_failure(representative)

    return ReflectionRecord(
        reflection_id=str(uuid4()),
        failure_class=failure_class,
        root_cause=representative,
        counterfactual="choose alternate tool path with lower latency and stricter prechecks",
        policy_patch=f"tighten policy around {failure_class}",
        memory_patch=f"store exemplar for {failure_class}",
    )


def evaluate_patch(request: EvaluatePatchRequest) -> EvaluatePatchResponse:
    reasons: list[str] = []
    delta = request.candidate_score - request.baseline_score

    if delta < 0:
        reasons.append("candidate score regresses baseline")
    if request.observed_p95_latency_ms > request.latency_budget_ms:
        reasons.append("latency budget exceeded")
    if request.error_budget_remaining < 0.2:
        reasons.append("insufficient error budget remaining")

    recommendation = "approve" if len(reasons) == 0 else "reject"
    return EvaluatePatchResponse(
        recommendation=recommendation,
        reasons=reasons,
        projected_delta=round(delta, 4),
    )

