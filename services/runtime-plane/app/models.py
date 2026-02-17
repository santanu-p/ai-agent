from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskTolerance(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class GoalSpec(BaseModel):
    goal_id: str
    intent: str
    constraints: list[str] = Field(default_factory=list)
    budget: float
    deadline: datetime
    risk_tolerance: RiskTolerance
    domains: list[str]


class ExecutionPolicy(BaseModel):
    tool_allowances: list[str]
    resource_limits: dict[str, Any]
    network_scope: str
    data_scope: str
    rollback_policy: str


class TaskTrace(BaseModel):
    trace_id: str
    goal_id: str
    steps: list[str]
    tool_calls: list[str]
    model_calls: list[str]
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


class ExecuteRequest(BaseModel):
    goal: GoalSpec
    policy: ExecutionPolicy
    max_iterations: int = 3


class ExecuteResponse(BaseModel):
    trace: TaskTrace
    reflections: list[ReflectionRecord]
    memory_entries: dict[str, list[str]]

