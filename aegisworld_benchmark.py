from __future__ import annotations

from dataclasses import dataclass
from statistics import quantiles
from typing import Any, Dict, List

from aegisworld_service import AegisWorldService


@dataclass
class BenchmarkResult:
    total_runs: int
    success_rate: float
    p95_latency_ms: float
    avg_token_cost: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runs": self.total_runs,
            "success_rate": self.success_rate,
            "p95_latency_ms": self.p95_latency_ms,
            "avg_token_cost": self.avg_token_cost,
        }


class BenchmarkRunner:
    """Runs synthetic goal executions against the in-memory service."""

    def __init__(self, service: AegisWorldService) -> None:
        self.service = service

    def run(self, runs: int = 10, domain: str = "dev") -> BenchmarkResult:
        agent = self.service.create_agent({"name": f"benchmark-{domain}"})

        outcomes: List[str] = []
        latencies: List[int] = []
        token_costs: List[int] = []

        for idx in range(runs):
            goal = self.service.create_goal(
                {
                    "intent": f"[{domain}] synthetic benchmark goal {idx}",
                    "domains": [domain],
                    "budget": 5.0,
                    "risk_tolerance": "medium",
                }
            )
            result = self.service.execute(agent["agent_id"], goal["goal_id"])
            trace = result["trace"]
            outcomes.append(trace["outcome"])
            latencies.append(int(trace["latency_ms"]))
            token_costs.append(int(trace["token_cost"]))

        success_count = len([o for o in outcomes if o == "success"])
        success_rate = (success_count / runs) if runs else 0.0

        if len(latencies) >= 2:
            # 20-quantiles => 95th percentile is last boundary.
            p95_latency_ms = float(quantiles(latencies, n=20)[-1])
        elif len(latencies) == 1:
            p95_latency_ms = float(latencies[0])
        else:
            p95_latency_ms = 0.0

        avg_token_cost = (sum(token_costs) / len(token_costs)) if token_costs else 0.0

        return BenchmarkResult(
            total_runs=runs,
            success_rate=success_rate,
            p95_latency_ms=p95_latency_ms,
            avg_token_cost=avg_token_cost,
        )
