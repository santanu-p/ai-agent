from __future__ import annotations

from fastapi import FastAPI

from app.engine import cluster_failures, evaluate_patch, synthesize_reflection
from app.models import (
    ClusterRequest,
    ClusterResult,
    EvaluatePatchRequest,
    EvaluatePatchResponse,
    ReflectionRecord,
    ReflectionRequest,
)

app = FastAPI(title="AegisWorld Learning Plane", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "learning-plane"}


@app.post("/v1/learning/cluster-failures", response_model=ClusterResult)
def cluster(req: ClusterRequest) -> ClusterResult:
    steps: list[str] = []
    for trace in req.traces:
        steps.extend(trace.steps)
    return cluster_failures(steps)


@app.post("/v1/learning/reflect", response_model=ReflectionRecord)
def reflect(req: ReflectionRequest) -> ReflectionRecord:
    return synthesize_reflection(req)


@app.post("/v1/learning/evaluate-patch", response_model=EvaluatePatchResponse)
def evaluate(req: EvaluatePatchRequest) -> EvaluatePatchResponse:
    return evaluate_patch(req)

