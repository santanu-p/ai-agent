from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.world_state import WorldState

SCHEMA_VERSION = 1


class PersistenceError(RuntimeError):
    """Persistence specific failures."""


def save_snapshot(world: WorldState, path: str | Path) -> Path:
    destination = Path(path)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "world": world.to_dict(),
    }
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return destination


def _migrate(payload: dict[str, Any]) -> dict[str, Any]:
    version = payload.get("schema_version", 0)
    if version == SCHEMA_VERSION:
        return payload
    if version == 0:
        payload["schema_version"] = 1
        world = payload.get("world", {})
        world.setdefault("chunk_size", 16)
        payload["world"] = world
        return payload
    raise PersistenceError(f"Unsupported schema version: {version}")


def load_snapshot(path: str | Path) -> WorldState:
    source = Path(path)
    if not source.exists():
        raise PersistenceError(f"Snapshot does not exist: {source}")
    payload = json.loads(source.read_text(encoding="utf-8"))
    migrated = _migrate(payload)
    return WorldState.from_dict(migrated["world"])
