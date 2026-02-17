from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .models import GeneratedPatch, GovernanceVerdict, MetricsSnapshot, RolloutDecision, VerificationResults


@dataclass(slots=True)
class IterationRecord:
    iteration_id: str
    metrics_snapshot: dict[str, Any]
    prompt_version: str
    prompt: str
    proposed_diff: str
    verification_results: dict[str, Any]
    governance_verdict: dict[str, Any]
    rollout_decision: dict[str, Any]
    rollback_pointer: str | None


class IterationStore:
    """Persists each loop iteration as a JSON artifact."""

    def __init__(self, root: str = "ai/improvement_loop/iterations") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def store(
        self,
        *,
        iteration_id: str,
        snapshot: MetricsSnapshot,
        proposal: GeneratedPatch,
        verification: VerificationResults,
        governance: GovernanceVerdict,
        rollout: RolloutDecision,
    ) -> Path:
        record = IterationRecord(
            iteration_id=iteration_id,
            metrics_snapshot=asdict(snapshot),
            prompt_version=proposal.prompt_version,
            prompt=proposal.prompt_text,
            proposed_diff=proposal.diff,
            verification_results=asdict(verification),
            governance_verdict=asdict(governance),
            rollout_decision=asdict(rollout),
            rollback_pointer=rollout.rollback_pointer,
        )

        destination = self.root / f"{iteration_id}.json"
        destination.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
        return destination
