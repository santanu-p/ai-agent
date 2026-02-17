from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MetricsSnapshot:
    """Observed gameplay telemetry used as optimization input."""

    timestamp: str
    retention_d1: float
    retention_d7: float
    quest_completion_rate: float
    top_death_causes: dict[str, int]
    economy_inflation_index: float
    active_sessions: int
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ObjectiveScores:
    """Per-objective and aggregate fitness scores."""

    overall_fitness: float
    score_components: dict[str, float]
    notes: str = ""


@dataclass
class GeneratedPatch:
    """Model-generated constrained patch proposal."""

    prompt_version: str
    prompt_text: str
    diff: str
    target_files: list[str]


@dataclass
class VerificationResults:
    """Outputs from static and simulation checks."""

    static_checks_passed: bool
    simulation_checks_passed: bool
    static_check_report: str
    simulation_report: str

    @property
    def passed(self) -> bool:
        return self.static_checks_passed and self.simulation_checks_passed


@dataclass
class RolloutDecision:
    """Release decision and rollback anchor."""

    decision: str
    canary_fraction: float
    reason: str
    rollback_pointer: str


@dataclass
class GovernanceVerdict:
    """Outcome and rationale of governance policy evaluation."""

    approved: bool
    rationale: list[str]
    composite_score: float
    guardrails_satisfied: bool
    missing_constraints: list[str]
    requires_human_approval: bool
    human_approval_granted: bool
    required_red_team_scenarios: list[str]
    provided_red_team_scenarios: list[str]


@dataclass
class IterationRecord:
    """Persisted artifact for one improvement-loop iteration."""

    iteration_id: str
    created_at: str
    input_metrics_snapshot: MetricsSnapshot
    objective_scores: ObjectiveScores
    prompt_version: str
    prompt_text: str
    proposed_diff: str
    verification_results: VerificationResults
    governance_verdict: GovernanceVerdict
    rollout_decision: RolloutDecision

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IterationStore:
    """JSON file-backed storage for optimization loop iterations."""

    def __init__(self, root: str | Path = "ai/improvement_loop/iterations") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, record: IterationRecord) -> Path:
        destination = self.root / f"{record.iteration_id}.json"
        destination.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
        return destination

    def load(self, iteration_id: str) -> IterationRecord:
        path = self.root / f"{iteration_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return IterationRecord(
            iteration_id=data["iteration_id"],
            created_at=data["created_at"],
            input_metrics_snapshot=MetricsSnapshot(**data["input_metrics_snapshot"]),
            objective_scores=ObjectiveScores(**data["objective_scores"]),
            prompt_version=data["prompt_version"],
            prompt_text=data["prompt_text"],
            proposed_diff=data["proposed_diff"],
            verification_results=VerificationResults(**data["verification_results"]),
            governance_verdict=GovernanceVerdict(**data["governance_verdict"]),
            rollout_decision=RolloutDecision(**data["rollout_decision"]),
        )
