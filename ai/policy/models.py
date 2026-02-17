from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

@dataclass(frozen=True)
class PerformanceBudget:
    frame_time_ms_p95_max: float
    memory_mb_peak_max: float

@dataclass(frozen=True)
class CanaryThresholds:
    max_error_rate: float
    max_p95_latency_ms: float
    max_timeout_rate: float

@dataclass(frozen=True)
class SaveCompatibilityRule:
    required_keys: tuple[str, ...]
    allowed_version_range: tuple[int, int]

@dataclass(frozen=True)
class AIPolicy:
    allowed_path_prefixes: tuple[str, ...]
    allowed_config_domains: tuple[str, ...]
    forbidden_apis: tuple[str, ...]
    lint_commands: tuple[str, ...]
    typecheck_commands: tuple[str, ...]
    replay_seed: int
    performance_budget: PerformanceBudget
    canary_thresholds: CanaryThresholds
    save_compatibility: SaveCompatibilityRule

@dataclass
class PatchContext:
    patch_id: str
    repo_path: Path
    changed_files: tuple[str, ...]
    changed_domains: tuple[str, ...]
    user_content_blobs: tuple[str, ...] = ()
    performance_metrics: dict[str, float] = field(default_factory=dict)
    canary_metrics: dict[str, float] = field(default_factory=dict)
    save_snapshots: tuple[dict[str, Any], ...] = ()
    replay_runner: Callable[[int], str] | None = None

@dataclass(frozen=True)
class GateResult:
    gate: str
    passed: bool
    details: str

@dataclass
class EnforcementReport:
    patch_id: str
    quarantined: bool
    gate_results: list[GateResult]
    quarantine_record: Path | None = None
    @property
    def failed_gates(self) -> Iterable[GateResult]:
        return (g for g in self.gate_results if not g.passed)
