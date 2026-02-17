from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from game.world.migrations import migrate_world_state
from game.world.state_schema import CURRENT_SCHEMA_VERSION, WorldDiff, WorldState


class IntegrityError(RuntimeError):
    pass


class WorldStore:
    """Persists full snapshots periodically and incremental diffs for every update."""

    def __init__(
        self,
        root_dir: str | Path = "data",
        snapshot_interval: int = 10,
        signature_key: str = "dev-world-signature-key",
    ) -> None:
        self.root = Path(root_dir)
        self.snapshots_dir = self.root / "snapshots"
        self.diffs_dir = self.root / "diffs"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.diffs_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_interval = max(1, snapshot_interval)
        self.signature_key = signature_key.encode("utf-8")

    def _canonical(self, payload: Dict[str, Any]) -> bytes:
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def _integrity_meta(self, payload: Dict[str, Any]) -> Dict[str, str]:
        encoded = self._canonical(payload)
        digest = hashlib.sha256(encoded).hexdigest()
        signature = hmac.new(self.signature_key, encoded, digestmod=hashlib.sha256).hexdigest()
        return {"sha256": digest, "signature": signature}

    def _write_record(self, path: Path, payload: Dict[str, Any]) -> None:
        record = {
            "payload": payload,
            "integrity": self._integrity_meta(payload),
        }
        path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")

    def _read_record(self, path: Path) -> Dict[str, Any]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        payload = raw["payload"]
        actual = self._integrity_meta(payload)
        expected = raw["integrity"]
        if expected["sha256"] != actual["sha256"]:
            raise IntegrityError(f"Hash mismatch: {path}")
        if not hmac.compare_digest(expected["signature"], actual["signature"]):
            raise IntegrityError(f"Signature mismatch: {path}")
        return payload

    def persist_update(self, base_state: WorldState, operations: List[Dict[str, Any]]) -> WorldState:
        new_state = apply_operations(base_state, operations)
        diff = WorldDiff(
            schema_version=CURRENT_SCHEMA_VERSION,
            base_world_version=base_state.world_version,
            target_world_version=new_state.world_version,
            tick=new_state.tick,
            operations=operations,
        )
        diff_path = self.diffs_dir / f"diff_{base_state.world_version:08d}_{new_state.world_version:08d}.json"
        self._write_record(diff_path, diff.to_dict())

        if new_state.world_version % self.snapshot_interval == 0:
            self.write_snapshot(new_state)

        return new_state

    def write_snapshot(self, state: WorldState) -> str:
        snapshot_id = f"snapshot_{state.world_version:08d}"
        path = self.snapshots_dir / f"{snapshot_id}.json"
        self._write_record(path, state.to_dict())
        return snapshot_id

    def load_snapshot(self, snapshot_id: str) -> WorldState:
        path = self.snapshots_dir / f"{snapshot_id}.json"
        payload = self._read_record(path)
        migrated = migrate_world_state(payload, target_version=CURRENT_SCHEMA_VERSION)
        return WorldState.from_dict(migrated)

    def list_snapshots(self) -> List[str]:
        def key(name: str) -> int:
            return int(name.split("_")[-1])

        snapshots = [path.stem for path in self.snapshots_dir.glob("snapshot_*.json")]
        return sorted(snapshots, key=key)

    def list_diffs(self) -> List[Path]:
        return sorted(self.diffs_dir.glob("diff_*.json"))

    def diff_stream_from(self, world_version: int) -> Iterable[WorldDiff]:
        for path in self.list_diffs():
            payload = self._read_record(path)
            diff = WorldDiff.from_dict(payload)
            if diff.base_world_version >= world_version:
                yield diff

    def load_latest_valid_snapshot(self) -> Optional[Tuple[str, WorldState]]:
        snapshots = reversed(self.list_snapshots())
        for snapshot_id in snapshots:
            path = self.snapshots_dir / f"{snapshot_id}.json"
            try:
                payload = self._read_record(path)
                migrated = migrate_world_state(payload, target_version=CURRENT_SCHEMA_VERSION)
                return snapshot_id, WorldState.from_dict(migrated)
            except (IntegrityError, json.JSONDecodeError, KeyError, ValueError):
                continue
        return None

    def recover_startup_state(self) -> WorldState:
        latest = self.load_latest_valid_snapshot()
        if latest is None:
            return WorldState(schema_version=CURRENT_SCHEMA_VERSION)

        _snapshot_id, state = latest
        for diff in self.diff_stream_from(state.world_version):
            # Reject broken chains and stop recovery at first inconsistency.
            if diff.base_world_version != state.world_version:
                break
            state = apply_operations(state, diff.operations)
        return state


def apply_operations(state: WorldState, operations: List[Dict[str, Any]]) -> WorldState:
    next_entities = dict(state.entities)
    for op in operations:
        kind = op.get("op")
        entity_id = op.get("entity_id")
        if kind == "set":
            next_entities[entity_id] = op.get("value", {})
        elif kind == "patch":
            base = dict(next_entities.get(entity_id, {}))
            base.update(op.get("value", {}))
            next_entities[entity_id] = base
        elif kind == "delete":
            next_entities.pop(entity_id, None)
        else:
            raise ValueError(f"Unsupported operation '{kind}'")

    return WorldState(
        schema_version=CURRENT_SCHEMA_VERSION,
        world_version=state.world_version + 1,
        seed=state.seed,
        tick=state.tick + 1,
        entities=next_entities,
        metadata=dict(state.metadata),
        created_at=state.created_at,
    )
