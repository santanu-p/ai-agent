from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ai.governance import objective_spec, policy_constraints, red_team_tests
from ai.governance.policy_constraints import RiskCategory
from ai.governance.red_team_tests import RedTeamCategory

from .models import GovernanceVerdict, RolloutDecision, VerificationResults


@dataclass
class ReleasePolicy:
    min_fitness_for_canary: float = 0.65
    min_governance_score: float = 0.7
    default_canary_fraction: float = 0.1
    max_canary_fraction: float = 0.5



class ReleaseManager:
    """Decides canary rollout fraction and rollback pointer."""

    def __init__(self, policy: ReleasePolicy | None = None) -> None:
        self.policy = policy or ReleasePolicy()

    def evaluate_governance(
        self,
        *,
        retention_score: float,
        challenge_score: float,
        fairness_score: float,
        performance_score: float,
        p95_latency_ms: int,
        crash_rate_delta_pct: float,
        economy_inflation_delta_pct: float,
        declared_constraint_ids: Iterable[str],
        risk_categories: Iterable[RiskCategory],
        human_approval_granted: bool,
        red_team_scenario_ids: Iterable[str] | None = None,
        red_team_categories: Iterable[RedTeamCategory] | None = None,
    ) -> GovernanceVerdict:
        composite_score = objective_spec.composite_score(
            retention=retention_score,
            challenge=challenge_score,
            fairness=fairness_score,
            performance=performance_score,
        )
        guardrails_ok = objective_spec.guardrails_satisfied(
            fairness_score=fairness_score,
            p95_latency_ms=p95_latency_ms,
            crash_rate_delta_pct=crash_rate_delta_pct,
            economy_inflation_delta_pct=economy_inflation_delta_pct,
        )

        missing_constraints = policy_constraints.validate_constraints(declared_constraint_ids)
        needs_human_approval = policy_constraints.requires_human_approval(risk_categories)

        provided_scenarios = set(red_team_scenario_ids or [])
        for category in red_team_categories or []:
            provided_scenarios.update(
                red_team_tests.scenario_ids(red_team_tests.scenarios_for(category))
            )

        required_scenarios = red_team_tests.scenario_ids(red_team_tests.RED_TEAM_SCENARIOS)
        red_team_coverage_ok = all(scenario in provided_scenarios for scenario in required_scenarios)

        rationale: list[str] = []
        if composite_score < self.policy.min_governance_score:
            rationale.append(
                f"Composite governance score {composite_score:.3f} below gate "
                f"{self.policy.min_governance_score:.3f}."
            )
        if not guardrails_ok:
            rationale.append("Objective guardrails were not satisfied.")
        if missing_constraints:
            rationale.append(
                "Missing required policy constraints: " + ", ".join(missing_constraints)
            )
        if needs_human_approval and not human_approval_granted:
            rationale.append("Human approval required for selected high-risk categories.")
        if not red_team_coverage_ok:
            rationale.append("Red-team scenario coverage is incomplete for production promotion.")

        if not rationale:
            rationale.append("Governance checks passed.")

        return GovernanceVerdict(
            approved=(
                composite_score >= self.policy.min_governance_score
                and guardrails_ok
                and not missing_constraints
                and (not needs_human_approval or human_approval_granted)
                and red_team_coverage_ok
            ),
            rationale=rationale,
            composite_score=composite_score,
            guardrails_satisfied=guardrails_ok,
            missing_constraints=missing_constraints,
            requires_human_approval=needs_human_approval,
            human_approval_granted=human_approval_granted,
            required_red_team_scenarios=required_scenarios,
            provided_red_team_scenarios=sorted(provided_scenarios),
        )

    def decide(
        self,
        fitness_score: float,
        verification: VerificationResults,
        previous_stable_version: str,
        governance: GovernanceVerdict | None = None,
    ) -> RolloutDecision:
        if governance is not None and not governance.approved:
            return RolloutDecision(
                decision="reject",
                canary_fraction=0.0,
                reason="Governance gate failed: " + " ".join(governance.rationale),
                rollback_pointer=previous_stable_version,
            )

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
