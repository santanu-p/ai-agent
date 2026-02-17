"""Schema migration registry for world state upgrades."""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping

from game.world.migrations.v1_to_v2 import migrate_v1_to_v2

MigrationFn = Callable[[Mapping[str, Any]], Dict[str, Any]]

MIGRATIONS: Dict[int, MigrationFn] = {
    1: migrate_v1_to_v2,
}


def migrate_world_state(state: Mapping[str, Any], target_version: int) -> Dict[str, Any]:
    current_version = int(state.get("version", 1))
    migrated: Dict[str, Any] = dict(state)

    while current_version < target_version:
        migration = MIGRATIONS.get(current_version)
        if migration is None:
            raise ValueError(f"Missing migration path from version {current_version}")
        migrated = migration(migrated)
        current_version = int(migrated["version"])

    if current_version != target_version:
        raise ValueError(f"Unexpected schema version after migration: {current_version}")

    return migrated
