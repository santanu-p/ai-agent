"""Snapshot/diff persistence, integrity checks, and startup recovery."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from game.world.migrations import migrate_world_state
from game.world.state_schema import (
    SCHEMA_VERSION,
    DiffEnvelope,
    SnapshotEnvelope,
    normalize_world_state,
    now_iso,
)


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _sign(payload_hash: str, signing_key: str) -> str:
    return hmac.new(signing_key.encode("utf-8"), payload_hash.encode("utf-8"), hashlib.sha256).hexdigest()


def _verify_signature(payload_hash: str, signature: str, signing_key: str) -> bool:
    expected = _sign(payload_hash, signing_key)
    return hmac.compare_digest(expected, signature)


def _entity_index(state: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {entity["entity_id"]: entity for entity in state.get("entities", [])}


def compute_diff(previous: Mapping[str, Any], current: Mapping[str, Any]) -> Dict[str, Any]:
    """Create deterministic entity-level incremental diff payload."""
    old_entities = _entity_index(previous)
    new_entities = _entity_index(current)

    added = [new_entities[eid] for eid in sorted(set(new_entities) - set(old_entities))]
    removed = sorted(set(old_entities) - set(new_entities))
    updated: List[Dict[str, Any]] = []

    for entity_id in sorted(set(old_entities) & set(new_entities)):
        if old_entities[entity_id] != new_entities[entity_id]:
            updated.append({"entity_id": entity_id, "before": old_entities[entity_id], "after": new_entities[entity_id]})

    metadata_changed = previous.get("metadata", {}) != current.get("metadata", {})

    return {
        "tick_from": int(previous["tick"]),
        "tick_to": int(current["tick"]),
        "added": added,
        "removed": removed,
        "updated": updated,
        "metadata_after": current.get("metadata", {}) if metadata_changed else None,
    }


def apply_diff(state: Mapping[str, Any], diff: Mapping[str, Any]) -> Dict[str, Any]:
    """Apply one diff payload to a world state deterministically."""
    result = normalize_world_state(state)
    entities = _entity_index(result)

    for entity_id in diff.get("removed", []):
        entities.pop(entity_id, None)

    for entity in diff.get("added", []):
        entities[entity["entity_id"]] = entity

    for update in diff.get("updated", []):
        entities[update["entity_id"]] = update["after"]

    result["entities"] = [entities[eid] for eid in sorted(entities)]
    result["tick"] = int(diff["tick_to"])
    if diff.get("metadata_after") is not None:
        result["metadata"] = dict(diff["metadata_after"])
    return normalize_world_state(result)


class WorldPersistenceManager:
    """Persists snapshots/diffs and recovers latest valid state at startup."""

    def __init__(
        self,
        data_root: str = "data",
        snapshot_interval_ticks: int = 10,
        signing_key: Optional[str] = None,
    ) -> None:
        self.data_root = Path(data_root)
        self.snapshot_dir = self.data_root / "snapshots"
        self.diff_dir = self.data_root / "diffs"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.diff_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_interval_ticks = max(1, snapshot_interval_ticks)
        self.signing_key = signing_key or os.getenv("WORLD_STATE_SIGNING_KEY", "dev-signing-key")
        self._last_state: Optional[Dict[str, Any]] = None

    def persist_tick(self, state: Mapping[str, Any]) -> Dict[str, str]:
        """Persist one tick; emit snapshot periodically and diff otherwise."""
        canonical = normalize_world_state(state)
        canonical = migrate_world_state(canonical, target_version=SCHEMA_VERSION)

        if self._last_state is None or canonical["tick"] % self.snapshot_interval_ticks == 0:
            snapshot_id = self.write_snapshot(canonical)
            self._last_state = canonical
            return {"snapshot_id": snapshot_id}

        diff_id = self.write_diff(self._last_state, canonical)
        self._last_state = canonical
        return {"diff_id": diff_id}

    def write_snapshot(self, state: Mapping[str, Any]) -> str:
        canonical = normalize_world_state(state)
        snapshot_id = f"snapshot-{canonical['tick']:012d}"
        payload_hash = _sha256(canonical)
        envelope = SnapshotEnvelope(
            snapshot_id=snapshot_id,
            created_at=now_iso(),
            state=canonical,
            state_hash=payload_hash,
            signature=_sign(payload_hash, self.signing_key),
        )
        path = self.snapshot_dir / f"{snapshot_id}.json"
        path.write_text(_canonical_json(asdict(envelope)) + "\n", encoding="utf-8")
        return snapshot_id

    def write_diff(self, previous: Mapping[str, Any], current: Mapping[str, Any]) -> str:
        prev = normalize_world_state(previous)
        curr = normalize_world_state(current)
        diff = compute_diff(prev, curr)
        diff_id = f"diff-{curr['tick']:012d}"
        payload_hash = _sha256(diff)
        envelope = DiffEnvelope(
            diff_id=diff_id,
            snapshot_id=f"snapshot-{prev['tick']:012d}",
            tick=int(curr["tick"]),
            created_at=now_iso(),
            changes=diff,
            diff_hash=payload_hash,
            signature=_sign(payload_hash, self.signing_key),
        )
        path = self.diff_dir / f"{diff_id}.json"
        path.write_text(_canonical_json(asdict(envelope)) + "\n", encoding="utf-8")
        return diff_id

    def load_latest_valid_snapshot(self) -> Dict[str, Any]:
        """Load the newest snapshot with valid hash/signature; returns empty baseline if none valid."""
        snapshots = sorted(self.snapshot_dir.glob("snapshot-*.json"), reverse=True)
        for path in snapshots:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                state = raw["state"]
                state_hash = _sha256(state)
                if raw.get("state_hash") != state_hash:
                    continue
                if not _verify_signature(state_hash, raw.get("signature", ""), self.signing_key):
                    continue
                migrated = migrate_world_state(state, target_version=SCHEMA_VERSION)
                self._last_state = normalize_world_state(migrated)
                return self._last_state
            except Exception:
                continue

        self._last_state = {
            "world_id": "default-world",
            "tick": 0,
            "entities": [],
            "metadata": {},
            "version": SCHEMA_VERSION,
        }
        return dict(self._last_state)

    def iter_valid_diffs(self, min_tick_exclusive: int = 0) -> Iterable[Dict[str, Any]]:
        for path in sorted(self.diff_dir.glob("diff-*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                changes = raw["changes"]
                diff_hash = _sha256(changes)
                if raw.get("tick", 0) <= min_tick_exclusive:
                    continue
                if raw.get("diff_hash") != diff_hash:
                    continue
                if not _verify_signature(diff_hash, raw.get("signature", ""), self.signing_key):
                    continue
                yield raw
            except Exception:
                continue
