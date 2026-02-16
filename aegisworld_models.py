from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
import uuid


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class GoalSpec:
    goal_id: str
    intent: str
    constraints: Dict[str, Any]
    budget: float
    deadline: str
    risk_tolerance: str
    domains: List[str]
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionPolicy:
    tool_allowances: List[str]
    resource_limits: Dict[str, Any]
    network_scope: str
    data_scope: str
    rollback_policy: str

    def allows_tool(self, tool_name: str) -> bool:
        return tool_name in self.tool_allowances or "*" in self.tool_allowances


@dataclass
class TaskTrace:
    trace_id: str
    goal_id: str
    agent_id: str
    steps: List[str]
    tool_calls: List[Dict[str, Any]]
    model_calls: List[Dict[str, Any]]
    latency_ms: int
    token_cost: int
    outcome: str
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReflectionRecord:
    record_id: str
    goal_id: str
    failure_class: str
    root_cause: str
    counterfactual: str
    policy_patch: Dict[str, Any]
    memory_patch: Dict[str, Any]
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SecurityIncident:
    incident_id: str
    signal_set: List[str]
    severity: str
    blast_radius: str
    auto_actions: List[str]
    verification_state: str
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AutonomousChangeSet:
    change_id: str
    target: str
    diff: Dict[str, Any]
    risk_score: float
    canary_result: str
    promotion_state: str
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
