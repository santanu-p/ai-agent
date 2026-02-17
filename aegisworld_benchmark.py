from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class BenchmarkResult:
    total_runs: int
    success_runs: int
    success_rate: float
    blocked_runs: int
    average_latency_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runs": self.total_runs,
            "success_runs": self.success_runs,
            "success_rate": self.success_rate,
            "blocked_runs": self.blocked_runs,
            "average_latency_ms": self.average_latency_ms,
        }


class BenchmarkRunner:
    def summarize_traces(self, traces: List[Dict[str, Any]]) -> BenchmarkResult:
        total = len(traces)
        success = sum(1 for t in traces if t.get("outcome") == "success")
        blocked = sum(1 for t in traces if str(t.get("outcome", "")).startswith("blocked:"))
        avg_latency = sum(int(t.get("latency_ms", 0)) for t in traces) / total if total else 0.0
        return BenchmarkResult(
            total_runs=total,
            success_runs=success,
            success_rate=(success / total) if total else 0.0,
            blocked_runs=blocked,
            average_latency_ms=avg_latency,
        )
