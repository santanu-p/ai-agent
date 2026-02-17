from __future__ import annotations

from typing import Iterable

from .models import IterationRecord, IterationStore, utc_now_iso
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
    ) -> IterationRecord:
        metrics = self.telemetry_collector.collect(events)
        scores = self.objective_evaluator.evaluate(metrics)
        patch = self.patch_generator.generate(metrics, scores)
        verification = self.patch_verifier.verify(patch)
        decision = self.release_manager.decide(
            fitness_score=scores.overall_fitness,
            verification=verification,
            previous_stable_version=previous_stable_version,
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
            rollout_decision=decision,
        )
        self.iteration_store.save(record)
        return record
