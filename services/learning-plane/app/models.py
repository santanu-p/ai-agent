from __future__ import annotations

from pydantic import BaseModel, Field


class TaskTrace(BaseModel):
    trace_id: str
    goal_id: str
    steps: list[str] = Field(default_factory=list)
    tool_calls: list[str] = Field(default_factory=list)
    model_calls: list[str] = Field(default_factory=list)
    latency_ms: int
    token_cost: float
    outcome: str


class ReflectionRecord(BaseModel):
    reflection_id: str
    failure_class: str
    root_cause: str
    counterfactual: str
    policy_patch: str
    memory_patch: str


class ClusterRequest(BaseModel):
    traces: list[TaskTrace]


class ClusterResult(BaseModel):
    clusters: dict[str, list[str]]


class ReflectionRequest(BaseModel):
    trace: TaskTrace
    context: str = ""


class EvaluatePatchRequest(BaseModel):
    baseline_score: float
    candidate_score: float
    latency_budget_ms: int = 15_000
    observed_p95_latency_ms: int
    error_budget_remaining: float


class EvaluatePatchResponse(BaseModel):
    recommendation: str
    reasons: list[str]
    projected_delta: float

