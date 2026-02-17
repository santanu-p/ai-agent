from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .models import GeneratedPatch, PatchProposal, VerificationResults, as_generated_patch


class TelemetryCollectorLike(Protocol):
    def collect(self, **telemetry_inputs: Any) -> Any: ...


class ObjectiveEvaluatorLike(Protocol):
    def evaluate(self, snapshot: Any) -> Any: ...


class PatchGeneratorLike(Protocol):
    def propose_patch(
        self,
        snapshot: Any,
        fitness: Any,
        constraints: list[str],
        target_files: list[str],
    ) -> PatchProposal | GeneratedPatch: ...


class PatchVerifierLike(Protocol):
    def verify(self, patch: GeneratedPatch) -> VerificationResults: ...


class ReleaseManagerLike(Protocol):
    def decide(
        self,
        *,
        verification: VerificationResults,
        candidate_revision: str,
        stable_revision: str,
        requested_fraction: float,
    ) -> Any: ...


class IterationStoreLike(Protocol):
    def store(
        self,
        *,
        iteration_id: str,
        snapshot: Any,
        proposal: PatchProposal | GeneratedPatch,
        verification: VerificationResults,
        rollout: Any,
    ) -> str | Path: ...


@dataclass(slots=True)
class ImprovementLoopResult:
    snapshot: Any
    fitness: Any
    proposal: PatchProposal | GeneratedPatch
    verification: VerificationResults
    rollout: Any
    iteration_path: str


class ImprovementLoopEngine:
    """Coordinates telemetry -> objective -> patch -> verify -> rollout -> persist."""

    def __init__(
        self,
        telemetry_collector: TelemetryCollectorLike,
        objective_evaluator: ObjectiveEvaluatorLike,
        patch_generator: PatchGeneratorLike,
        patch_verifier: PatchVerifierLike,
        release_manager: ReleaseManagerLike,
        iteration_store: IterationStoreLike,
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
        telemetry_inputs: dict[str, Any],
        constraints: list[str],
        target_files: list[str],
        candidate_revision: str,
        stable_revision: str,
        requested_canary_fraction: float,
    ) -> ImprovementLoopResult:
        snapshot = self.telemetry_collector.collect(**telemetry_inputs)
        fitness = self.objective_evaluator.evaluate(snapshot)
        proposal = self.patch_generator.propose_patch(snapshot, fitness, constraints, target_files)
        verification = self.patch_verifier.verify(as_generated_patch(proposal))
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
