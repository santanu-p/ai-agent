"""Policy evaluation and regression gates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


@dataclass
class EvaluationThresholds:
    min_fun_proxy_delta: float = 0.0
    max_stability_error_rate: float = 0.02
    max_exploit_rate: float = 0.01
    max_cpu_ms_per_tick: float = 2.0


class PolicyEvaluator:
    """Runs regression gates for candidate policy promotion."""

    def __init__(self, thresholds: EvaluationThresholds | None = None) -> None:
        self.thresholds = thresholds or EvaluationThresholds()

    def evaluate(
        self,
        baseline_metrics: Dict[str, float],
        candidate_metrics: Dict[str, float],
    ) -> Dict[str, object]:
        gates: List[Tuple[str, bool, str]] = []

        fun_delta = candidate_metrics.get("fun_proxy", 0.0) - baseline_metrics.get("fun_proxy", 0.0)
        gates.append(
            (
                "fun_proxy",
                fun_delta >= self.thresholds.min_fun_proxy_delta,
                f"delta={fun_delta:.4f}, required>={self.thresholds.min_fun_proxy_delta:.4f}",
            )
        )

        stability_error = candidate_metrics.get("stability_error_rate", 1.0)
        gates.append(
            (
                "stability",
                stability_error <= self.thresholds.max_stability_error_rate,
                f"error={stability_error:.4f}, max={self.thresholds.max_stability_error_rate:.4f}",
            )
        )

        exploit_rate = candidate_metrics.get("exploit_rate", 1.0)
        gates.append(
            (
                "exploit_detection",
                exploit_rate <= self.thresholds.max_exploit_rate,
                f"rate={exploit_rate:.4f}, max={self.thresholds.max_exploit_rate:.4f}",
            )
        )

        cpu_budget = candidate_metrics.get("cpu_ms_per_tick", float("inf"))
        gates.append(
            (
                "cpu_budget",
                cpu_budget <= self.thresholds.max_cpu_ms_per_tick,
                f"cpu={cpu_budget:.4f}ms, max={self.thresholds.max_cpu_ms_per_tick:.4f}ms",
            )
        )

        passed = all(result for _, result, _ in gates)
        return {
            "passed": passed,
            "gates": [
                {"gate": name, "passed": result, "details": details}
                for name, result, details in gates
            ],
        }

    def compare_cohorts(self, control: Iterable[float], canary: Iterable[float]) -> Dict[str, float]:
        control_values = list(control)
        canary_values = list(canary)
        if not control_values:
            raise ValueError("Control cohort has no data")
        if not canary_values:
            raise ValueError("Canary cohort has no data")

        control_mean = sum(control_values) / len(control_values)
        canary_mean = sum(canary_values) / len(canary_values)
        return {
            "control_mean": control_mean,
            "canary_mean": canary_mean,
            "delta": canary_mean - control_mean,
        }


__all__ = ["EvaluationThresholds", "PolicyEvaluator"]
