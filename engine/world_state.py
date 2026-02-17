from __future__ import annotations

from dataclasses import asdict, dataclass, field
from random import Random
from typing import Any


@dataclass
class Entity:
    entity_id: str
    name: str
    x: int
    y: int
    health: int = 100


@dataclass
class Chunk:
    chunk_id: tuple[int, int]
    terrain_seed: int
    terrain_type: str
    resources: dict[str, int] = field(default_factory=dict)


@dataclass
class Weather:
    condition: str = "clear"
    temperature_c: float = 20.0


@dataclass
class TimeOfDay:
    tick: int = 0
    hour: int = 6
    minute: int = 0


@dataclass
class WorldState:
    seed: int
    chunk_size: int = 16
    chunks: dict[tuple[int, int], Chunk] = field(default_factory=dict)
    entities: dict[str, Entity] = field(default_factory=dict)
    weather: Weather = field(default_factory=Weather)
    time_of_day: TimeOfDay = field(default_factory=TimeOfDay)

    @classmethod
    def bootstrap(cls, seed: int, chunk_radius: int = 1) -> "WorldState":
        rng = Random(seed)
        world = cls(seed=seed)
        terrain_types = ["plains", "forest", "desert", "hills"]

        for cx in range(-chunk_radius, chunk_radius + 1):
            for cy in range(-chunk_radius, chunk_radius + 1):
                terrain_seed = rng.randint(0, 10**9)
                terrain = terrain_types[(terrain_seed + cx + cy) % len(terrain_types)]
                resources = {
                    "wood": max(0, 25 + ((terrain_seed // 3) % 20) - abs(cx * 2)),
                    "stone": max(0, 18 + ((terrain_seed // 5) % 15) - abs(cy * 2)),
                    "food": max(0, 30 + ((terrain_seed // 7) % 25) - abs(cx + cy)),
                }
                world.chunks[(cx, cy)] = Chunk(
                    chunk_id=(cx, cy),
                    terrain_seed=terrain_seed,
                    terrain_type=terrain,
                    resources=resources,
                )

        world.weather = Weather(
            condition=["clear", "cloudy", "windy", "rain"][(seed // 17) % 4],
            temperature_c=10 + (seed % 20),
        )
        return world

    def add_entity(self, entity: Entity) -> None:
        self.entities[entity.entity_id] = entity

    def get_chunk_at(self, x: int, y: int) -> Chunk:
        chunk_x = x // self.chunk_size
        chunk_y = y // self.chunk_size
        key = (chunk_x, chunk_y)
        if key not in self.chunks:
            generated_seed = abs(hash((self.seed, key))) % (10**9)
            self.chunks[key] = Chunk(
                chunk_id=key,
                terrain_seed=generated_seed,
                terrain_type="plains",
                resources={"wood": 10, "stone": 10, "food": 10},
            )
        return self.chunks[key]

    def step_time(self, minutes: int = 1) -> None:
        self.time_of_day.tick += 1
        total_minutes = self.time_of_day.hour * 60 + self.time_of_day.minute + minutes
        self.time_of_day.hour = (total_minutes // 60) % 24
        self.time_of_day.minute = total_minutes % 60

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "chunk_size": self.chunk_size,
            "chunks": {
                f"{cx},{cy}": asdict(chunk)
                for (cx, cy), chunk in sorted(self.chunks.items())
            },
            "entities": {entity_id: asdict(entity) for entity_id, entity in sorted(self.entities.items())},
            "weather": asdict(self.weather),
            "time_of_day": asdict(self.time_of_day),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorldState":
        world = cls(seed=payload["seed"], chunk_size=payload.get("chunk_size", 16))
        for key, chunk_data in payload.get("chunks", {}).items():
            cx_str, cy_str = key.split(",")
            chunk = Chunk(
                chunk_id=(int(cx_str), int(cy_str)),
                terrain_seed=chunk_data["terrain_seed"],
                terrain_type=chunk_data["terrain_type"],
                resources=dict(chunk_data.get("resources", {})),
            )
            world.chunks[chunk.chunk_id] = chunk

        for entity_id, entity_data in payload.get("entities", {}).items():
            world.entities[entity_id] = Entity(
                entity_id=entity_id,
                name=entity_data["name"],
                x=entity_data["x"],
                y=entity_data["y"],
                health=entity_data.get("health", 100),
            )

        weather = payload.get("weather", {})
        world.weather = Weather(
            condition=weather.get("condition", "clear"),
            temperature_c=weather.get("temperature_c", 20.0),
        )

        tod = payload.get("time_of_day", {})
        world.time_of_day = TimeOfDay(
            tick=tod.get("tick", 0),
            hour=tod.get("hour", 6),
            minute=tod.get("minute", 0),
        )
        return world
