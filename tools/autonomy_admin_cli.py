#!/usr/bin/env python3
"""Inspect recent autonomous AI changes and outcomes."""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Iterable


def load_entries(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []

    entries: list[dict] = []
    for raw_line in log_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            entries.append({"action": "invalid", "raw": line})
    return entries


def render_table(entries: Iterable[dict]) -> str:
    rows = ["timestamp\taction\tchange_id\toutcome\tsummary"]
    for item in entries:
        outcome = ""
        if item.get("action") == "applied":
            outcome = "success" if item.get("success") == "true" else "failed"
        if item.get("action") == "reverted":
            outcome = f"reverted:{item.get('reason', '')}"
        rows.append(
            "\t".join(
                [
                    str(item.get("timestamp", "")),
                    str(item.get("action", "")),
                    str(item.get("change_id", "")),
                    outcome,
                    str(item.get("summary", "")),
                ]
            )
        )
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log",
        default="logs/autonomy_audit.log",
        help="Path to autonomy audit log (default: logs/autonomy_audit.log)",
    )
    parser.add_argument("--limit", type=int, default=20, help="Max entries to display")
    parser.add_argument(
        "--json", action="store_true", help="Emit JSON instead of tabular output"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print action/outcome counters",
    )

    args = parser.parse_args()
    entries = load_entries(Path(args.log))
    recent = entries[-args.limit :]

    if args.summary:
        actions = Counter(entry.get("action", "unknown") for entry in recent)
        applied = [e for e in recent if e.get("action") == "applied"]
        successes = sum(1 for e in applied if e.get("success") == "true")
        failures = len(applied) - successes
        print("summary")
        print(f"  total: {len(recent)}")
        print(f"  actions: {dict(actions)}")
        print(f"  applied_success: {successes}")
        print(f"  applied_failures: {failures}")
        return 0

    if args.json:
        print(json.dumps(recent, indent=2))
        return 0

    print(render_table(recent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
