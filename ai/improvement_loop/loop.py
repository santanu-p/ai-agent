from __future__ import annotations

from typing import Iterable

from ai.governance.policy_constraints import RiskCategory
from ai.governance.red_team_tests import RedTeamCategory

from .models import GovernanceVerdict, IterationRecord, IterationStore, utc_now_iso
from .objective_evaluator import ObjectiveEvaluator
from .patch_generator import PatchGenerator
from .patch_verifier import PatchVerifier
from .release_manager import ReleaseManager
from .telemetry_collector import SessionEvent, TelemetryCollector


class ImprovementLoop:
    """Coordinates telemetry -> objective -> patch -> verification -> release."""

    def __init__(
        self,
        telemetry_collector: TelemetryCollector,
        objective_evaluator: ObjectiveEvaluator,
        patch_generator: PatchGenerator,
        patch_verifier: PatchVerifier,
        release_manager: ReleaseManager,
        iteration_store: IterationStore,
    ) -> None:
        self.telemetry_collector = telemetry_collector
        self.objective_evaluator = objective_evaluator
        self.patch_generator = patch_generator
        self.patch_verifier = patch_verifier
        self.release_manager = release_manager
        self.iteration_store = iteration_store

    def run_iteration(
        self,
        iteration_id: str,
        events: Iterable[SessionEvent],
        previous_stable_version: str,
        *,
        declared_constraint_ids: Iterable[str] | None = None,
        risk_categories: Iterable[RiskCategory] = (),
        human_approval_granted: bool = False,
        red_team_scenario_ids: Iterable[str] = (),
        red_team_categories: Iterable[RedTeamCategory] = (),
    ) -> IterationRecord:
        metrics = self.telemetry_collector.collect(events)
        scores = self.objective_evaluator.evaluate(metrics)
        patch = self.patch_generator.generate(metrics, scores)
        verification = self.patch_verifier.verify(patch)

        governance: GovernanceVerdict
        governance_for_release: GovernanceVerdict | None = None
        if declared_constraint_ids is None:
            governance = GovernanceVerdict(
                approved=True,
                rationale=["Governance evaluation skipped (legacy invocation)."],
                composite_score=0.0,
                guardrails_satisfied=True,
                missing_constraints=[],
                requires_human_approval=False,
                human_approval_granted=False,
                required_red_team_scenarios=[],
                provided_red_team_scenarios=[],
            )
        else:
            governance = self.release_manager.evaluate_governance(
                retention_score=scores.score_components.get("retention", 0.0),
                challenge_score=scores.score_components.get("progression", 0.0),
                fairness_score=scores.score_components.get("economy", 0.0),
                performance_score=scores.score_components.get("stability", 0.0),
                p95_latency_ms=int(metrics.extra.get("p95_latency_ms", 0)),
                crash_rate_delta_pct=float(metrics.extra.get("crash_rate_delta_pct", 0.0)),
                economy_inflation_delta_pct=abs(metrics.economy_inflation_index),
                declared_constraint_ids=declared_constraint_ids,
                risk_categories=risk_categories,
                human_approval_granted=human_approval_granted,
                red_team_scenario_ids=red_team_scenario_ids,
                red_team_categories=red_team_categories,
            )
            governance_for_release = governance

        decision = self.release_manager.decide(
            fitness_score=scores.overall_fitness,
            verification=verification,
            previous_stable_version=previous_stable_version,
            governance=governance_for_release,
        )

        record = IterationRecord(
            iteration_id=iteration_id,
            created_at=utc_now_iso(),
            input_metrics_snapshot=metrics,
            objective_scores=scores,
            prompt_version=patch.prompt_version,
            prompt_text=patch.prompt_text,
            proposed_diff=patch.diff,
            verification_results=verification,
            governance_verdict=governance,
            rollout_decision=decision,
        )
        self.iteration_store.save(record)
        return record
