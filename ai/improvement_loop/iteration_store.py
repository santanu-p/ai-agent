from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .patch_generator import PatchProposal
from .patch_verifier import VerificationResult
from .release_manager import RolloutDecision
from .telemetry_collector import MetricsSnapshot


@dataclass(slots=True)
class IterationRecord:
    iteration_id: str
    metrics_snapshot: dict[str, Any]
    prompt_version: str
    prompt: str
    proposed_diff: str
    verification_results: dict[str, Any]
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
        proposal: PatchProposal,
        verification: VerificationResult,
        rollout: RolloutDecision,
    ) -> Path:
        record = IterationRecord(
            iteration_id=iteration_id,
            metrics_snapshot=snapshot.to_dict(),
            prompt_version=proposal.prompt_version,
            prompt=proposal.prompt,
            proposed_diff=proposal.proposed_diff,
            verification_results={
                "passed": verification.passed,
                "checks": [asdict(check) for check in verification.checks],
            },
            rollout_decision=asdict(rollout),
            rollback_pointer=rollout.rollback_pointer,
        )

        destination = self.root / f"{iteration_id}.json"
        destination.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
        return destination
