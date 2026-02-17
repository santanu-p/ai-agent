#!/usr/bin/env python3
"""Run AI patch simulations, emit artifacts, and fail on KPI regression."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from scenarios import SimulationSuite


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run simulation KPI gate")
    parser.add_argument("--patch-version", default="local", help="Patch identifier (e.g., commit SHA)")
    parser.add_argument(
        "--baseline",
        default="tests/simulation/baseline_metrics.json",
        help="Path to baseline KPI metrics",
    )
    parser.add_argument(
        "--artifact-dir",
        default="artifacts/simulation",
        help="Directory where artifacts and reports are generated",
    )
    return parser.parse_args()


def load_baseline(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return {item["name"]: float(item["value"]) for item in data.get("metrics", [])}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def write_markdown_report(
    path: Path,
    patch_version: str,
    created_at: str,
    metrics: list[dict],
    failures: list[dict],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Simulation Report ({patch_version})",
        "",
        f"Generated: `{created_at}`",
        "",
        "| Scenario | KPI | Comparator | Threshold | Current | Baseline | Delta | Status |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for metric in metrics:
        lines.append(
            "| {name} | {metric_name} | {comparator} | {threshold:.4f} | {value:.4f} | {baseline:.4f} | {delta:+.4f} | {status} |".format(
                **metric,
                status="PASS" if metric["passed"] else "FAIL",
            )
        )

    lines.append("")
    if failures:
        lines.append("## KPI Gate Result: ❌ FAILED")
        lines.append("")
        lines.append("Failed scenarios:")
        for item in failures:
            lines.append(f"- `{item['name']}` ({item['metric_name']}: {item['value']:.4f} {item['comparator']} {item['threshold']:.4f})")
    else:
        lines.append("## KPI Gate Result: ✅ PASSED")

    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    suite = SimulationSuite(seed=42)
    baseline = load_baseline(Path(args.baseline))
    created_at = datetime.now(timezone.utc).isoformat()

    scenario_results = suite.run_all()
    metrics = []
    failures = []

    for result in scenario_results:
        baseline_value = baseline.get(result.name, result.value)
        delta = result.value - baseline_value
        metric_payload = {
            **asdict(result),
            "baseline": baseline_value,
            "delta": delta,
            "passed": result.passed,
        }
        metrics.append(metric_payload)
        if not result.passed:
            failures.append(metric_payload)

    payload = {
        "patch_version": args.patch_version,
        "generated_at": created_at,
        "metrics": metrics,
        "failed": failures,
    }

    artifact_dir = Path(args.artifact_dir)
    json_path = artifact_dir / f"results-{args.patch_version}.json"
    report_path = artifact_dir / f"report-{args.patch_version}.md"

    write_json(json_path, payload)
    write_markdown_report(report_path, args.patch_version, created_at, metrics, failures)

    print(f"Wrote JSON results to {json_path}")
    print(f"Wrote markdown report to {report_path}")

    if failures:
        print("Simulation KPI gate failed.")
        return 1

    print("Simulation KPI gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
