"""AI adaptation subsystem."""

from .loop import AdaptiveAILoop, DeploymentLedger, PatchVersion
from .metrics import KPIReadings, KPIThresholds
from .patch_format import AIPatch, DeltaOperation, PATCH_JSON_SCHEMA
from .validator import (
    PatchValidator,
    PerformanceBudget,
    RuntimeStats,
    SimulationResult,
    ValidationReport,
)

__all__ = [
    "AdaptiveAILoop",
    "AIPatch",
    "DeltaOperation",
    "DeploymentLedger",
    "KPIReadings",
    "KPIThresholds",
    "PATCH_JSON_SCHEMA",
    "PatchValidator",
    "PatchVersion",
    "PerformanceBudget",
    "RuntimeStats",
    "SimulationResult",
    "ValidationReport",
]
