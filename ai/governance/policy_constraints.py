"""Non-negotiable policy constraints for AI-driven changes.

These constraints are designed to protect player trust and system integrity.
Any planning, simulation, or automated patch generation must pass these
constraints before a change can be proposed for approval.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List


class RiskCategory(str, Enum):
    """Risk classes used by governance approval checks."""

    ECONOMY_REWRITE = "economy_rewrite"
    COMBAT_BALANCE_SWING = "combat_balance_swing"
    PERSISTENCE_MIGRATION = "persistence_migration"
    LOW_RISK = "low_risk"


@dataclass(frozen=True)
class ConstraintResult:
    """Result of evaluating a policy constraint."""

    passed: bool
    rule_id: str
    message: str


NON_NEGOTIABLE_RULES = {
    "R1_NO_SAVE_CORRUPTION": "Changes must preserve save compatibility and data integrity.",
    "R2_NO_PAY_TO_WIN_DRIFT": "Changes must not increase monetization-linked power advantages.",
    "R3_NO_HIDDEN_UNFAIR_NERFS": "Changes must not apply undisclosed nerfs that reduce fairness.",
}

HIGH_RISK_CATEGORIES_REQUIRING_HUMAN_APPROVAL = {
    RiskCategory.ECONOMY_REWRITE,
    RiskCategory.COMBAT_BALANCE_SWING,
    RiskCategory.PERSISTENCE_MIGRATION,
}


def requires_human_approval(risk_categories: Iterable[RiskCategory]) -> bool:
    """Return True if any high-risk category is present."""

    return any(category in HIGH_RISK_CATEGORIES_REQUIRING_HUMAN_APPROVAL for category in risk_categories)


def evaluate_non_negotiables(
    *,
    save_corruption_risk: bool,
    pay_to_win_drift_risk: bool,
    hidden_nerf_risk: bool,
) -> List[ConstraintResult]:
    """Evaluate core non-negotiable safety constraints.

    The caller must provide risk flags from analysis, simulation, or audits.
    """

    checks = [
        (
            "R1_NO_SAVE_CORRUPTION",
            not save_corruption_risk,
            "Potential save corruption detected.",
        ),
        (
            "R2_NO_PAY_TO_WIN_DRIFT",
            not pay_to_win_drift_risk,
            "Potential pay-to-win drift detected.",
        ),
        (
            "R3_NO_HIDDEN_UNFAIR_NERFS",
            not hidden_nerf_risk,
            "Potential hidden unfair nerf detected.",
        ),
    ]

    return [
        ConstraintResult(passed=passed, rule_id=rule_id, message=message)
        for rule_id, passed, message in checks
    ]


def assert_constraints(results: Iterable[ConstraintResult]) -> None:
    """Raise ValueError if any non-negotiable constraint fails."""

    failures = [r for r in results if not r.passed]
    if failures:
        details = "; ".join(f"{f.rule_id}: {f.message}" for f in failures)
        raise ValueError(f"Constraint violation(s): {details}")
