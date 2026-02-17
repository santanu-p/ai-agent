"""World state data models for the deterministic simulation runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import random

ChunkCoord = Tuple[int, int]


@dataclass
class Entity:
    """Entity record tracked by the world state."""

    entity_id: str
    kind: str
    position: Tuple[int, int]
    health: int = 100
    inventory: Dict[str, int] = field(default_factory=dict)


@dataclass
class Chunk:
    """A lazily generated chunk containing local data."""

    coord: ChunkCoord
    terrain_seed: int
    resources: Dict[str, int]
    entity_ids: List[str] = field(default_factory=list)


@dataclass
class WeatherState:
    kind: str = "clear"
    temperature_c: float = 20.0


@dataclass
class TimeOfDay:
    day: int = 0
    tick_of_day: int = 0
    ticks_per_day: int = 24000

    def advance(self, ticks: int = 1) -> None:
        self.tick_of_day += ticks
        while self.tick_of_day >= self.ticks_per_day:
            self.tick_of_day -= self.ticks_per_day
            self.day += 1


@dataclass
class WorldState:
    """Top-level world state with deterministic chunk generation."""

    world_seed: int
    tick: int = 0
    chunks: Dict[ChunkCoord, Chunk] = field(default_factory=dict)
    entities: Dict[str, Entity] = field(default_factory=dict)
    weather: WeatherState = field(default_factory=WeatherState)
    time_of_day: TimeOfDay = field(default_factory=TimeOfDay)

    def get_or_create_chunk(self, coord: ChunkCoord) -> Chunk:
        chunk = self.chunks.get(coord)
        if chunk:
            return chunk

        rng = random.Random(self.world_seed ^ (coord[0] * 73856093) ^ (coord[1] * 19349663))
        terrain_seed = rng.randint(0, 2**31 - 1)
        resources = {
            "wood": rng.randint(20, 80),
            "stone": rng.randint(20, 80),
            "food": rng.randint(10, 40),
        }
        chunk = Chunk(coord=coord, terrain_seed=terrain_seed, resources=resources)
        self.chunks[coord] = chunk
        return chunk

    def add_entity(self, entity: Entity) -> None:
        self.entities[entity.entity_id] = entity
        chunk_coord = world_to_chunk(entity.position)
        chunk = self.get_or_create_chunk(chunk_coord)
        if entity.entity_id not in chunk.entity_ids:
            chunk.entity_ids.append(entity.entity_id)


def world_to_chunk(position: Tuple[int, int], chunk_size: int = 16) -> ChunkCoord:
    """Map world coordinates to chunk coordinates."""

    x, y = position
    return x // chunk_size, y // chunk_size
