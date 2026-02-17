from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence


class PatchStatus(str, Enum):
    """Lifecycle state for an AI-authored patch."""

    PENDING = "pending"
    APPROVED = "approved"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class PerformanceBudget:
    """Ceilings that must not be exceeded by patch runtime metrics."""

    max_frame_time_ms: float
    max_memory_mb: float


@dataclass(frozen=True)
class TelemetryGate:
    """Thresholds used for canary gate validation."""

    metric_name: str
    max_allowed_value: float


@dataclass(frozen=True)
class SaveCompatibilityConfig:
    """Supported save versions for backward compatibility checks."""

    minimum_supported_version: int
    current_version: int


@dataclass
class PatchManifest:
    """Structured payload describing the candidate patch and its reports."""

    patch_id: str
    changed_files: List[str]
    changed_domains: List[str]
    imported_symbols: List[str]
    user_content: str
    static_lint_passed: bool
    static_typecheck_passed: bool
    replay_run_hashes: List[str]
    perf_frame_time_ms: float
    perf_memory_mb: float
    save_from_version: int
    save_to_version: int
    canary_telemetry: Dict[str, float]


@dataclass
class PolicyConfig:
    """Policy constraints that govern whether a patch can be accepted."""

    allowed_file_prefixes: Sequence[str]
    allowed_domains: Sequence[str]
    forbidden_apis: Sequence[str]
    performance_budget: PerformanceBudget
    save_compatibility: SaveCompatibilityConfig
    telemetry_gates: Sequence[TelemetryGate]
    prompt_injection_markers: Sequence[str] = field(
        default_factory=lambda: (
            "ignore previous instructions",
            "system prompt",
            "developer message",
            "reveal hidden prompt",
            "jailbreak",
            "act as",
        )
    )


@dataclass
class GateResult:
    """Result of a single gate check."""

    name: str
    passed: bool
    reason: str


@dataclass
class EvaluationReport:
    """Output of full policy evaluation run."""

    patch_id: str
    status: PatchStatus
    gate_results: List[GateResult]
    quarantined_reason: Optional[str] = None

    @property
    def failed_gates(self) -> List[GateResult]:
        return [result for result in self.gate_results if not result.passed]


RevertCallback = Callable[[PatchManifest], Any]
