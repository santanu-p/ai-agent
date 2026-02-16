"""Demand-based chunk streaming around active players."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Dict, Iterable, List, Set, Tuple


ChunkCoord = Tuple[int, int]


@dataclass
class PlayerState:
    player_id: str
    x: float
    y: float


@dataclass
class ChunkStreamingDecision:
    to_load: List[ChunkCoord] = field(default_factory=list)
    to_unload: List[ChunkCoord] = field(default_factory=list)
    keep_loaded: List[ChunkCoord] = field(default_factory=list)


class ChunkLoader:
    """Tracks active interest sets and computes load/unload decisions.

    Uses hysteresis: unload radius is larger than load radius to avoid chunk
    thrashing when players hover around boundaries.
    """

    def __init__(
        self,
        chunk_size: int,
        load_radius: int = 3,
        unload_radius: int = 5,
        max_load_per_tick: int = 32,
    ) -> None:
        if unload_radius < load_radius:
            raise ValueError("unload_radius must be >= load_radius")
        self.chunk_size = chunk_size
        self.load_radius = load_radius
        self.unload_radius = unload_radius
        self.max_load_per_tick = max_load_per_tick
        self._loaded: Set[ChunkCoord] = set()

    @property
    def loaded_chunks(self) -> Set[ChunkCoord]:
        return set(self._loaded)

    def update(self, players: Iterable[PlayerState]) -> ChunkStreamingDecision:
        players_list = list(players)
        desired = self._desired_chunks(players_list, self.load_radius)
        keep = self._desired_chunks(players_list, self.unload_radius)

        to_load = [chunk for chunk in desired if chunk not in self._loaded]
        to_load.sort(key=lambda c: self._priority(c, players_list))
        to_load = to_load[: self.max_load_per_tick]

        to_unload = [chunk for chunk in self._loaded if chunk not in keep]
        to_unload.sort()

        for chunk in to_load:
            self._loaded.add(chunk)
        for chunk in to_unload:
            self._loaded.remove(chunk)

        keep_loaded = sorted(self._loaded)
        return ChunkStreamingDecision(to_load=to_load, to_unload=to_unload, keep_loaded=keep_loaded)

    def _desired_chunks(self, players: List[PlayerState], radius: int) -> Set[ChunkCoord]:
        desired: Set[ChunkCoord] = set()
        for p in players:
            center = self._world_to_chunk(p.x, p.y)
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if dx * dx + dy * dy <= radius * radius:
                        desired.add((center[0] + dx, center[1] + dy))
        return desired

    def _priority(self, chunk: ChunkCoord, players: List[PlayerState]) -> float:
        if not players:
            return 0.0
        cx, cy = self._chunk_to_center(chunk)
        return min((cx - p.x) ** 2 + (cy - p.y) ** 2 for p in players)

    def _world_to_chunk(self, x: float, y: float) -> ChunkCoord:
        return (math.floor(x / self.chunk_size), math.floor(y / self.chunk_size))

    def _chunk_to_center(self, chunk: ChunkCoord) -> Tuple[float, float]:
        x, y = chunk
        return (
            x * self.chunk_size + self.chunk_size / 2.0,
            y * self.chunk_size + self.chunk_size / 2.0,
        )
