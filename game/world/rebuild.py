"""Rebuild deterministic world state from snapshot + valid diffs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from game.world.migrations import migrate_world_state
from game.world.persistence import _sha256, _verify_signature, apply_diff
from game.world.state_schema import SCHEMA_VERSION, normalize_world_state


def rebuild_world(
    snapshot_id: Optional[str],
    data_root: str = "data",
    signing_key: str = "dev-signing-key",
) -> Dict[str, Any]:
    """Reconstruct deterministic world state from a specific snapshot id.

    If snapshot_id is None, picks the latest valid snapshot.
    """
    snapshot_dir = Path(data_root) / "snapshots"
    diff_dir = Path(data_root) / "diffs"

    if snapshot_id is None:
        candidates = sorted(snapshot_dir.glob("snapshot-*.json"), reverse=True)
    else:
        candidates = [snapshot_dir / f"{snapshot_id}.json"]

    base_state: Optional[Dict[str, Any]] = None

    for snapshot_path in candidates:
        if not snapshot_path.exists():
            continue
        raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
        state = raw["state"]
        state_hash = _sha256(state)
        if state_hash != raw.get("state_hash"):
            continue
        if not _verify_signature(state_hash, raw.get("signature", ""), signing_key):
            continue
        base_state = normalize_world_state(migrate_world_state(state, target_version=SCHEMA_VERSION))
        break

    if base_state is None:
        raise ValueError("No valid snapshot found for rebuild")

    for diff_path in sorted(diff_dir.glob("diff-*.json")):
        raw = json.loads(diff_path.read_text(encoding="utf-8"))
        if raw.get("tick", 0) <= base_state["tick"]:
            continue
        changes = raw["changes"]
        diff_hash = _sha256(changes)
        if diff_hash != raw.get("diff_hash"):
            continue
        if not _verify_signature(diff_hash, raw.get("signature", ""), signing_key):
            continue
        base_state = apply_diff(base_state, changes)

    return normalize_world_state(base_state)
