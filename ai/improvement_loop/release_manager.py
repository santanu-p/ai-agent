from __future__ import annotations

from dataclasses import dataclass

from .models import RolloutDecision, VerificationResults


@dataclass
class ReleasePolicy:
    min_fitness_for_canary: float = 0.65
    default_canary_fraction: float = 0.1
    max_canary_fraction: float = 0.5


class ReleaseManager:
    """Decides canary rollout fraction and rollback pointer."""

    def __init__(self, policy: ReleasePolicy | None = None) -> None:
        self.policy = policy or ReleasePolicy()

    def decide(
        self,
        fitness_score: float,
        verification: VerificationResults,
        previous_stable_version: str,
    ) -> RolloutDecision:
        if not verification.passed:
            return RolloutDecision(
                decision="reject",
                canary_fraction=0.0,
                reason="Verification failed.",
                rollback_pointer=previous_stable_version,
            )

        if fitness_score >= self.policy.min_fitness_for_canary:
            fraction = min(
                self.policy.max_canary_fraction,
                max(self.policy.default_canary_fraction, fitness_score / 2),
            )
            return RolloutDecision(
                decision="canary",
                canary_fraction=round(fraction, 3),
                reason="Fitness and verification passed.",
                rollback_pointer=previous_stable_version,
            )

        return RolloutDecision(
            decision="hold",
            canary_fraction=0.0,
            reason="Fitness below threshold.",
            rollback_pointer=previous_stable_version,
        )
