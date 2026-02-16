from __future__ import annotations

from dataclasses import dataclass

from .patch_verifier import VerificationResult


@dataclass(slots=True)
class RolloutDecision:
    approved: bool
    canary_fraction: float
    reason: str
    rollback_pointer: str | None


class ReleaseManager:
    """Handles canary rollout decisions and rollback pointers."""

    def __init__(self, max_canary_fraction: float = 0.1) -> None:
        self.max_canary_fraction = max_canary_fraction

    def decide(
        self,
        *,
        verification: VerificationResult,
        candidate_revision: str,
        stable_revision: str,
        requested_fraction: float,
    ) -> RolloutDecision:
        if not verification.passed:
            return RolloutDecision(
                approved=False,
                canary_fraction=0.0,
                reason="Verification failed",
                rollback_pointer=stable_revision,
            )

        canary_fraction = min(max(requested_fraction, 0.0), self.max_canary_fraction)
        return RolloutDecision(
            approved=True,
            canary_fraction=canary_fraction,
            reason="Approved for canary rollout",
            rollback_pointer=stable_revision if candidate_revision != stable_revision else None,
        )
