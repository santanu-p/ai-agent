from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ai.governance.policy_constraints import RiskCategory
from ai.governance.red_team_tests import RedTeamCategory

from .iteration_store import IterationStore
from .models import GeneratedPatch, GovernanceVerdict, MetricsSnapshot, ObjectiveScores, RolloutDecision, VerificationResults
from .objective_evaluator import ObjectiveEvaluator
from .patch_generator import PatchGenerator
from .patch_verifier import PatchVerifier
from .release_manager import ReleaseManager
from .telemetry_collector import TelemetryCollector


@dataclass(slots=True)
class ImprovementLoopResult:
    snapshot: MetricsSnapshot
    fitness: ObjectiveScores
    proposal: GeneratedPatch
    verification: VerificationResults
    governance: GovernanceVerdict
    rollout: RolloutDecision
    iteration_path: str


class ImprovementLoopEngine:
    """Coordinates telemetry -> objective -> patch -> verify -> governance -> rollout."""

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
        *,
        iteration_id: str,
        telemetry_inputs: dict,
        previous_stable_version: str,
        declared_constraint_ids: Iterable[str],
        risk_categories: Iterable[RiskCategory] = (),
        human_approval_granted: bool = False,
        red_team_scenario_ids: Iterable[str] = (),
        red_team_categories: Iterable[RedTeamCategory] = (),
    ) -> ImprovementLoopResult:
        snapshot = self.telemetry_collector.collect(**telemetry_inputs)
        fitness = self.objective_evaluator.evaluate(snapshot)
        proposal = self.patch_generator.generate(snapshot, fitness)
        verification = self.patch_verifier.verify(proposal)

        governance = self.release_manager.evaluate_governance(
            retention_score=fitness.score_components.get("retention", 0.0),
            challenge_score=fitness.score_components.get("progression", 0.0),
            fairness_score=fitness.score_components.get("economy", 0.0),
            performance_score=fitness.score_components.get("stability", 0.0),
            p95_latency_ms=int(snapshot.extra.get("p95_latency_ms", 0)),
            crash_rate_delta_pct=float(snapshot.extra.get("crash_rate_delta_pct", 0.0)),
            economy_inflation_delta_pct=abs(snapshot.economy_inflation_index),
            declared_constraint_ids=declared_constraint_ids,
            risk_categories=risk_categories,
            human_approval_granted=human_approval_granted,
            red_team_scenario_ids=red_team_scenario_ids,
            red_team_categories=red_team_categories,
        )

        rollout = self.release_manager.decide(
            fitness_score=fitness.overall_fitness,
            verification=verification,
            previous_stable_version=previous_stable_version,
            governance=governance,
        )
        iteration_path = self.iteration_store.store(
            iteration_id=iteration_id,
            snapshot=snapshot,
            proposal=proposal,
            verification=verification,
            governance=governance,
            rollout=rollout,
        )

        return ImprovementLoopResult(
            snapshot=snapshot,
            fitness=fitness,
            proposal=proposal,
            verification=verification,
            governance=governance,
            rollout=rollout,
            iteration_path=str(iteration_path),
        )
