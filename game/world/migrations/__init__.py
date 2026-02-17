from __future__ import annotations

from typing import Any, Callable, Dict

from game.world.state_schema import CURRENT_SCHEMA_VERSION

MigrationFn = Callable[[Dict[str, Any]], Dict[str, Any]]


# Map "from_version" -> migration function to next version.
MIGRATIONS: dict[int, MigrationFn] = {}


def register(from_version: int) -> Callable[[MigrationFn], MigrationFn]:
    def decorator(func: MigrationFn) -> MigrationFn:
        MIGRATIONS[from_version] = func
        return func

    return decorator


def migrate_world_state(payload: Dict[str, Any], target_version: int = CURRENT_SCHEMA_VERSION) -> Dict[str, Any]:
    state = dict(payload)
    version = state.get("schema_version", 1)

    if version > target_version:
        raise ValueError(f"Cannot downgrade schema from {version} to {target_version}")

    while version < target_version:
        migration = MIGRATIONS.get(version)
        if migration is None:
            raise ValueError(f"No migration path from schema version {version}")
        state = migration(state)
        version = state["schema_version"]

    return state


# Ensure migration modules are imported so decorators register them.
from game.world.migrations import v1_to_v2  # noqa: E402,F401
