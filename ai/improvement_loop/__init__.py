"""Improvement loop package for telemetry-driven game tuning."""

from .engine import ImprovementLoopEngine, ImprovementLoopResult
from .iteration_store import IterationStore, IterationRecord
from .objective_evaluator import ObjectiveEvaluator, ObjectiveWeights, FitnessScore
from .patch_generator import PatchGenerator, PatchProposal
from .patch_verifier import PatchVerifier, VerificationResult, VerificationCheck
from .release_manager import ReleaseManager, RolloutDecision
from .telemetry_collector import TelemetryCollector, MetricsSnapshot

__all__ = [
    "ImprovementLoopEngine",
    "ImprovementLoopResult",
    "IterationStore",
    "IterationRecord",
    "ObjectiveEvaluator",
    "ObjectiveWeights",
    "FitnessScore",
    "PatchGenerator",
    "PatchProposal",
    "PatchVerifier",
    "VerificationResult",
    "VerificationCheck",
    "ReleaseManager",
    "RolloutDecision",
    "TelemetryCollector",
    "MetricsSnapshot",
]
