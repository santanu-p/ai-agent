"""Hard safety and product constraints for AI-driven game/system changes.

These constraints are non-negotiable and should be evaluated before any
AI-authored proposal is allowed to proceed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List


class RiskCategory(str, Enum):
    """Change categories used for approval and risk escalation."""

    ECONOMY_REWRITE = "economy_rewrite"
    COMBAT_BALANCE_SWING = "combat_balance_swing"
    PERSISTENCE_MIGRATION = "persistence_migration"
    CONTENT_TUNING = "content_tuning"
    UX_IMPROVEMENT = "ux_improvement"


@dataclass(frozen=True)
class PolicyConstraint:
    """A non-negotiable policy requirement."""

    id: str
    title: str
    rationale: str


NON_NEGOTIABLE_CONSTRAINTS: tuple[PolicyConstraint, ...] = (
    PolicyConstraint(
        id="safety.no_save_corruption",
        title="No save corruption",
        rationale=(
            "AI changes must not break save compatibility, corrupt player state, "
            "or create irreversible data loss."
        ),
    ),
    PolicyConstraint(
        id="product.no_pay_to_win_drift",
        title="No pay-to-win drift",
        rationale=(
            "AI tuning must not advantage spenders in core progression, power, "
            "or competitive outcomes."
        ),
    ),
    PolicyConstraint(
        id="fairness.no_hidden_nerfs",
        title="No unfair hidden nerfs",
        rationale=(
            "AI systems must not introduce materially negative balancing changes "
            "without transparent player-facing disclosure."
        ),
    ),
)


HIGH_RISK_CATEGORIES: frozenset[RiskCategory] = frozenset(
    {
        RiskCategory.ECONOMY_REWRITE,
        RiskCategory.COMBAT_BALANCE_SWING,
        RiskCategory.PERSISTENCE_MIGRATION,
    }
)


def requires_human_approval(categories: Iterable[RiskCategory]) -> bool:
    """Return True when any high-risk category is present.

    High-risk categories require explicit human approval prior to deployment.
    """

    return any(category in HIGH_RISK_CATEGORIES for category in categories)


def validate_constraints(asserted_constraint_ids: Iterable[str]) -> List[str]:
    """Return missing non-negotiable constraint IDs.

    Args:
        asserted_constraint_ids: Constraint IDs that a proposal claims to satisfy.

    Returns:
        Missing constraint IDs. Empty list means all required constraints are present.
    """

    asserted = set(asserted_constraint_ids)
    required = {constraint.id for constraint in NON_NEGOTIABLE_CONSTRAINTS}
    return sorted(required - asserted)
