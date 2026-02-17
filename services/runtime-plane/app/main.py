from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.kernel import AgentKernel
from app.memory import TieredMemory
from app.models import ExecuteRequest, ExecuteResponse
from app.policy import evaluate
from app.tool_registry import ToolRegistry

app = FastAPI(title="AegisWorld Runtime Plane", version="0.1.0")
memory = TieredMemory()
tools = ToolRegistry()
kernel = AgentKernel(memory=memory, tool_registry=tools)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "runtime-plane"}


@app.post("/v1/runtime/execute", response_model=ExecuteResponse)
def execute_runtime(request: ExecuteRequest) -> ExecuteResponse:
    decision = evaluate(request.policy)
    if not decision.allowed:
        raise HTTPException(status_code=422, detail={"error": "policy_denied", "reasons": decision.reasons})
    return kernel.execute(request)

