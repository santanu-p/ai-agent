"""Persistence layer for world snapshots with schema migration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from engine.world_state import Entity, TimeOfDay, WeatherState, WorldState

CURRENT_SCHEMA_VERSION = 2


def save_world(world: WorldState, path: str | Path) -> None:
    payload = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "world_seed": world.world_seed,
        "tick": world.tick,
        "weather": {
            "kind": world.weather.kind,
            "temperature_c": world.weather.temperature_c,
        },
        "time_of_day": {
            "day": world.time_of_day.day,
            "tick_of_day": world.time_of_day.tick_of_day,
            "ticks_per_day": world.time_of_day.ticks_per_day,
        },
        "chunks": [
            {
                "coord": list(chunk.coord),
                "terrain_seed": chunk.terrain_seed,
                "resources": chunk.resources,
                "entity_ids": chunk.entity_ids,
            }
            for chunk in sorted(world.chunks.values(), key=lambda c: c.coord)
        ],
        "entities": [
            {
                "entity_id": entity.entity_id,
                "kind": entity.kind,
                "position": list(entity.position),
                "health": entity.health,
                "inventory": entity.inventory,
            }
            for entity in sorted(world.entities.values(), key=lambda e: e.entity_id)
        ],
    }

    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_world(path: str | Path) -> WorldState:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    data = migrate_snapshot(raw)

    world = WorldState(world_seed=data["world_seed"])
    world.tick = data["tick"]
    world.weather = WeatherState(**data["weather"])
    world.time_of_day = TimeOfDay(**data["time_of_day"])

    for chunk_data in data["chunks"]:
        coord = tuple(chunk_data["coord"])
        chunk = world.get_or_create_chunk(coord)
        chunk.terrain_seed = chunk_data["terrain_seed"]
        chunk.resources = chunk_data["resources"]
        chunk.entity_ids = chunk_data["entity_ids"]

    for entity_data in data["entities"]:
        entity = Entity(
            entity_id=entity_data["entity_id"],
            kind=entity_data["kind"],
            position=tuple(entity_data["position"]),
            health=entity_data["health"],
            inventory=entity_data["inventory"],
        )
        world.entities[entity.entity_id] = entity

    return world


def migrate_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    version = snapshot.get("schema_version", 1)
    data = dict(snapshot)

    if version < 2:
        data.setdefault("weather", {"kind": "clear", "temperature_c": 20.0})
        data["schema_version"] = 2
        version = 2

    if version != CURRENT_SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema version: {version}")

    data.setdefault("time_of_day", {"day": 0, "tick_of_day": 0, "ticks_per_day": 24000})
    data.setdefault("chunks", [])
    data.setdefault("entities", [])
    data.setdefault("tick", 0)
    return data
