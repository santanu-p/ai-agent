from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass(slots=True)
class Observation:
    """Runtime telemetry and evaluation artifacts collected from game sessions."""

    run_id: str
    retention_proxy: float
    quest_completion_time_minutes: float
    npc_interaction_quality: float
    simulation_regression_failures: int
    frame_time_ms_p95: float
    exploit_findings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class KPIReport:
    """Computed KPIs for a run and its comparison baseline."""

    retention_proxy: float
    quest_completion_time_minutes: float
    npc_interaction_quality: float
    baseline_retention_proxy: float
    baseline_completion_time_minutes: float
    baseline_npc_quality: float


@dataclass(slots=True)
class PatchProposal:
    """Policy-only patch proposal."""

    patch_id: str
    version_hint: str
    patch_payload: Dict[str, Any]
    authored_at: datetime


@dataclass(slots=True)
class ValidationResult:
    """Validation gates output for a patch proposal."""

    passed: bool
    reasons: List[str] = field(default_factory=list)


@dataclass(slots=True)
class DeploymentRecord:
    """Track deployed patch versions for rollback and audit."""

    version: int
    patch_id: str
    deployed_at: datetime
    kpi_report: KPIReport
    reverted: bool = False
