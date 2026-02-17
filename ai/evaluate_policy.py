"""Regression and readiness gates for AI policy candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping


@dataclass(frozen=True)
class EvaluationThresholds:
    min_fun_proxy: float = 0.62
    min_stability: float = 0.95
    max_exploit_risk: float = 0.15
    max_cpu_ms_per_tick: float = 1.2


class PolicyEvaluator:
    """Evaluates policy candidates against production gating thresholds."""

    def __init__(self, thresholds: EvaluationThresholds | None = None) -> None:
        self.thresholds = thresholds or EvaluationThresholds()

    def evaluate(self, candidate_metrics: Mapping[str, float]) -> Dict[str, object]:
        gates = {
            "fun_proxy": float(candidate_metrics.get("fun_proxy", 0.0)) >= self.thresholds.min_fun_proxy,
            "stability": float(candidate_metrics.get("stability", 0.0)) >= self.thresholds.min_stability,
            "exploit_detection": float(candidate_metrics.get("exploit_risk", 1.0)) <= self.thresholds.max_exploit_risk,
            "cpu_budget": float(candidate_metrics.get("cpu_ms_per_tick", 999.0)) <= self.thresholds.max_cpu_ms_per_tick,
        }
        passed = all(gates.values())
        reasons = [name for name, ok in gates.items() if not ok]
        return {"passed": passed, "gates": gates, "failed_reasons": reasons}
