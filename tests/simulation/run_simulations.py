#!/usr/bin/env python3
"""Simulation suite for AI patch validation.

Runs deterministic simulation scenarios and evaluates KPI thresholds against a
versioned baseline. Emits artifacts suitable for CI archival and regression
analysis.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class ScenarioResult:
    name: str
    metrics: dict[str, float]


def _rng(seed: int = 42) -> random.Random:
    return random.Random(seed)


def economy_stress_test() -> ScenarioResult:
    """Simulate inflation/solvency behavior under repeated shocks."""

    rng = _rng(1001)
    prices = [100.0]
    bankruptcies = 0
    agents = 300

    for _ in range(120):
        shock = rng.uniform(-0.018, 0.015)
        demand = 1.0 + rng.uniform(-0.04, 0.08)
        supply = 1.0 + rng.uniform(-0.07, 0.06)
        adjustment = 1 + shock + (demand - supply) * 0.045
        next_price = max(20.0, prices[-1] * adjustment)
        prices.append(next_price)

        insolvency_risk = max(0.0, (next_price - 138.0) / 700.0)
        for _ in range(agents // 12):
            if rng.random() < insolvency_risk:
                bankruptcies += 1

    inflation_rate = (prices[-1] - prices[0]) / prices[0]
    volatility = statistics.pstdev(prices) / statistics.mean(prices)
    bankruptcy_rate = bankruptcies / agents
    return ScenarioResult(
        name="economy_stress_test",
        metrics={
            "inflation_rate": inflation_rate,
            "price_volatility": volatility,
            "bankruptcy_rate": bankruptcy_rate,
        },
    )


def combat_difficulty_progression() -> ScenarioResult:
    """Simulate win-rates by level and verify smooth progression."""

    rng = _rng(1002)
    win_rates = []
    monotonic_penalties = 0

    for level in range(1, 11):
        wins = 0
        attempts = 500
        expected = max(0.15, 0.78 - level * 0.06)
        for _ in range(attempts):
            swing = rng.uniform(-0.04, 0.04)
            if rng.random() < expected + swing:
                wins += 1
        rate = wins / attempts
        win_rates.append(rate)

    for i in range(1, len(win_rates)):
        if win_rates[i] > win_rates[i - 1] + 0.03:
            monotonic_penalties += 1

    return ScenarioResult(
        name="combat_difficulty_progression",
        metrics={
            "early_win_rate": win_rates[0],
            "late_win_rate": win_rates[-1],
            "progression_drop": win_rates[0] - win_rates[-1],
            "monotonic_penalties": float(monotonic_penalties),
        },
    )


def quest_deadlock_detection() -> ScenarioResult:
    """Run deadlock analysis on quest state machine graphs."""

    graphs = {
        "quest_alpha": {
            "start": ["investigate", "skip"],
            "investigate": ["find_key", "combat"],
            "combat": ["find_key"],
            "find_key": ["unlock_gate"],
            "skip": ["unlock_gate"],
            "unlock_gate": ["complete"],
            "complete": [],
        },
        "quest_beta": {
            "start": ["gather", "trade"],
            "gather": ["craft"],
            "trade": ["craft"],
            "craft": ["deliver"],
            "deliver": ["complete"],
            "complete": [],
        },
    }

    deadlocks = 0
    completion_coverage = []

    for graph in graphs.values():
        reached = set()
        q = deque(["start"])
        while q:
            node = q.popleft()
            if node in reached:
                continue
            reached.add(node)
            for nxt in graph.get(node, []):
                q.append(nxt)

        terminal_nodes = [n for n, edges in graph.items() if not edges]
        if "complete" not in reached:
            deadlocks += 1
        if any(t != "complete" for t in terminal_nodes):
            deadlocks += 1

        completion_coverage.append(1.0 if "complete" in reached else 0.0)

    return ScenarioResult(
        name="quest_deadlock_detection",
        metrics={
            "deadlock_count": float(deadlocks),
            "completion_coverage": float(sum(completion_coverage) / len(completion_coverage)),
        },
    )


def _path_exists(grid: list[list[int]], start: tuple[int, int], goal: tuple[int, int]) -> tuple[bool, int]:
    n = len(grid)
    q = deque([(start, 0)])
    seen = {start}

    while q:
        (x, y), d = q.popleft()
        if (x, y) == goal:
            return True, d
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < n and grid[nx][ny] == 0 and (nx, ny) not in seen:
                seen.add((nx, ny))
                q.append(((nx, ny), d + 1))

    return False, 0


def npc_navigation_pathing_robustness() -> ScenarioResult:
    """Measure pathfinding success over noisy obstacle maps."""

    rng = _rng(1003)
    trials = 80
    successes = 0
    lengths = []

    for _ in range(trials):
        n = 14
        grid = [[0 if rng.random() > 0.22 else 1 for _ in range(n)] for _ in range(n)]
        start, goal = (0, 0), (n - 1, n - 1)
        grid[0][0] = 0
        grid[n - 1][n - 1] = 0

        found, dist = _path_exists(grid, start, goal)
        if found:
            successes += 1
            manhattan = (n - 1) * 2
            lengths.append(dist / manhattan)

    success_rate = successes / trials
    avg_path_detour = statistics.mean(lengths) if lengths else 999.0
    return ScenarioResult(
        name="npc_navigation_pathing_robustness",
        metrics={
            "path_success_rate": success_rate,
            "avg_path_detour": avg_path_detour,
        },
    )


def save_load_migration_invariants() -> ScenarioResult:
    """Validate that save/load migrations preserve gameplay invariants."""

    saves = [
        {
            "version": 1,
            "player": {"name": "Ari", "level": 12, "gold": 450},
            "quests": [{"id": "Q1", "status": "complete"}],
            "inventory": ["sword", "potion", "key"],
        },
        {
            "version": 2,
            "player": {"name": "Bo", "level": 4, "gold": 95},
            "quests": [{"id": "Q2", "status": "active"}],
            "inventory": ["dagger"],
        },
    ]

    def migrate(save: dict[str, Any]) -> dict[str, Any]:
        out = json.loads(json.dumps(save))
        if out["version"] == 1:
            out["economy"] = {"shards": out["player"].pop("gold")}
            out["version"] = 2
        if out["version"] == 2:
            out["player"]["xp"] = out["player"]["level"] * 100
            out["version"] = 3
        return out

    invariant_failures = 0

    for save in saves:
        migrated = migrate(save)
        if migrated["version"] != 3:
            invariant_failures += 1
        if not migrated["player"]["name"]:
            invariant_failures += 1
        if migrated["player"]["level"] < 1:
            invariant_failures += 1
        if "inventory" not in migrated or not isinstance(migrated["inventory"], list):
            invariant_failures += 1
        if any(q["status"] not in {"active", "complete", "failed"} for q in migrated["quests"]):
            invariant_failures += 1

    return ScenarioResult(
        name="save_load_migration_invariants",
        metrics={
            "migration_invariant_failures": float(invariant_failures),
            "migration_success_rate": float(1 - invariant_failures / (len(saves) * 5)),
        },
    )


def load_baseline(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_thresholds(
    results: list[ScenarioResult], baseline: dict[str, Any]
) -> tuple[list[dict[str, Any]], bool]:
    failures: list[dict[str, Any]] = []

    for result in results:
        scenario_cfg = baseline["scenarios"][result.name]
        for metric_name, value in result.metrics.items():
            metric_cfg = scenario_cfg[metric_name]
            min_v = metric_cfg.get("min")
            max_v = metric_cfg.get("max")
            passed = True
            if min_v is not None and value < min_v:
                passed = False
            if max_v is not None and value > max_v:
                passed = False
            if not passed:
                failures.append(
                    {
                        "scenario": result.name,
                        "metric": metric_name,
                        "value": value,
                        "threshold": metric_cfg,
                    }
                )

    return failures, not failures


def write_artifacts(
    output_dir: Path, version: str, results: list[ScenarioResult], failures: list[dict[str, Any]]
) -> None:
    version_dir = output_dir / version
    version_dir.mkdir(parents=True, exist_ok=True)

    metrics_payload = {r.name: r.metrics for r in results}
    metrics_file = version_dir / "simulation_metrics.json"
    metrics_file.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    comparison_json = version_dir / "comparison_report.json"
    comparison_json.write_text(
        json.dumps(
            {
                "version": version,
                "status": "pass" if not failures else "fail",
                "failure_count": len(failures),
                "failures": failures,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    report_lines = [
        f"# Simulation Comparison Report ({version})",
        "",
        f"Status: **{'PASS' if not failures else 'FAIL'}**",
        "",
    ]
    if failures:
        report_lines.append("## KPI Threshold Failures")
        for failure in failures:
            report_lines.append(
                f"- `{failure['scenario']}.{failure['metric']}` = {failure['value']:.4f} outside {failure['threshold']}"
            )
    else:
        report_lines.append("All KPI thresholds satisfied.")

    (version_dir / "comparison_report.md").write_text("\n".join(report_lines), encoding="utf-8")


def run_all() -> list[ScenarioResult]:
    scenarios: list[Callable[[], ScenarioResult]] = [
        economy_stress_test,
        combat_difficulty_progression,
        quest_deadlock_detection,
        npc_navigation_pathing_robustness,
        save_load_migration_invariants,
    ]
    return [scenario() for scenario in scenarios]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="tests/simulation/baselines/kpi_baseline.json")
    parser.add_argument("--output-dir", default="artifacts/simulations")
    parser.add_argument("--version", default="local")
    args = parser.parse_args()

    baseline = load_baseline(Path(args.baseline))
    results = run_all()
    failures, ok = evaluate_thresholds(results, baseline)
    write_artifacts(Path(args.output_dir), args.version, results, failures)

    print(json.dumps({"ok": ok, "failures": failures}, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
