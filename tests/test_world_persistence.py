from __future__ import annotations

import json
from pathlib import Path

from game.world.migrations import migrate_world_state
from game.world.rebuild import rebuild_world
from game.world.state_schema import WorldState
from game.world.storage import WorldStore


def test_periodic_snapshot_and_diffs(tmp_path: Path) -> None:
    store = WorldStore(root_dir=tmp_path / "data", snapshot_interval=2, signature_key="secret")
    state = WorldState(seed=42)
    store.write_snapshot(state)

    state = store.persist_update(state, [{"op": "set", "entity_id": "npc_1", "value": {"hp": 10}}])
    state = store.persist_update(state, [{"op": "patch", "entity_id": "npc_1", "value": {"hp": 11}}])

    snapshots = store.list_snapshots()
    diffs = store.list_diffs()

    assert "snapshot_00000000" in snapshots
    assert "snapshot_00000002" in snapshots
    assert len(diffs) == 2


def test_rebuild_world_is_deterministic(tmp_path: Path) -> None:
    store = WorldStore(root_dir=tmp_path / "data", snapshot_interval=2, signature_key="secret")
    state = WorldState(seed=123)
    snapshot_id = store.write_snapshot(state)

    state = store.persist_update(state, [{"op": "set", "entity_id": "unit", "value": {"x": 1}}])
    state = store.persist_update(state, [{"op": "patch", "entity_id": "unit", "value": {"x": 3, "y": 2}}])

    rebuilt_a = rebuild_world(snapshot_id, store=store)
    rebuilt_b = rebuild_world(snapshot_id, store=store)

    assert rebuilt_a.world_version == rebuilt_b.world_version
    assert rebuilt_a.tick == rebuilt_b.tick
    assert rebuilt_a.entities == rebuilt_b.entities
    assert rebuilt_a.entities["unit"] == {"x": 3, "y": 2}


def test_migration_v1_to_v2() -> None:
    legacy = {
        "schema_version": 1,
        "world_version": 1,
        "seed": 7,
        "tick": 5,
        "entities": {},
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    }

    migrated = migrate_world_state(legacy, target_version=2)
    assert migrated["schema_version"] == 2
    assert migrated["metadata"] == {}


def test_startup_recovery_uses_latest_valid_snapshot(tmp_path: Path) -> None:
    store = WorldStore(root_dir=tmp_path / "data", snapshot_interval=2, signature_key="secret")
    state = WorldState(seed=99)
    store.write_snapshot(state)

    state = store.persist_update(state, [{"op": "set", "entity_id": "boss", "value": {"hp": 100}}])
    store.write_snapshot(state)

    # Corrupt newest snapshot; recovery should skip it and use previous valid snapshot.
    newest = tmp_path / "data" / "snapshots" / "snapshot_00000001.json"
    raw = json.loads(newest.read_text(encoding="utf-8"))
    raw["payload"]["tick"] = 9999
    newest.write_text(json.dumps(raw), encoding="utf-8")

    recovered = store.recover_startup_state()
    assert recovered.world_version == 1
    assert recovered.entities["boss"]["hp"] == 100
