from __future__ import annotations

from dataclasses import dataclass

from .iteration_store import IterationStore
from .objective_evaluator import FitnessScore, ObjectiveEvaluator
from .patch_generator import PatchGenerator, PatchProposal
from .patch_verifier import PatchVerifier, VerificationResult
from .release_manager import ReleaseManager, RolloutDecision
from .telemetry_collector import MetricsSnapshot, TelemetryCollector


@dataclass(slots=True)
class ImprovementLoopResult:
    snapshot: MetricsSnapshot
    fitness: FitnessScore
    proposal: PatchProposal
    verification: VerificationResult
    rollout: RolloutDecision
    iteration_path: str


class ImprovementLoopEngine:
    """Coordinates telemetry -> objective -> patch -> verify -> rollout -> persist."""

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
        constraints: list[str],
        target_files: list[str],
        candidate_revision: str,
        stable_revision: str,
        requested_canary_fraction: float,
    ) -> ImprovementLoopResult:
        snapshot = self.telemetry_collector.collect(**telemetry_inputs)
        fitness = self.objective_evaluator.evaluate(snapshot)
        proposal = self.patch_generator.propose_patch(snapshot, fitness, constraints, target_files)
        verification = self.patch_verifier.verify()
        rollout = self.release_manager.decide(
            verification=verification,
            candidate_revision=candidate_revision,
            stable_revision=stable_revision,
            requested_fraction=requested_canary_fraction,
        )
        iteration_path = self.iteration_store.store(
            iteration_id=iteration_id,
            snapshot=snapshot,
            proposal=proposal,
            verification=verification,
            rollout=rollout,
        )

        return ImprovementLoopResult(
            snapshot=snapshot,
            fitness=fitness,
            proposal=proposal,
            verification=verification,
            rollout=rollout,
            iteration_path=str(iteration_path),
        )
