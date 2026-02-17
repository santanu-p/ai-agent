"""Chunk load/unload orchestration based on player movement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Protocol, Set, Tuple

from .terrain_generator import TerrainChunk, TerrainGenerator


ChunkCoord = Tuple[int, int]


class ChunkLifecycleHook(Protocol):
    """AI-facing chunk lifecycle hooks."""

    def on_chunk_loaded(self, chunk: TerrainChunk) -> None: ...

    def apply_spawn_rules(self, chunk: TerrainChunk) -> None: ...

    def inject_quests(self, chunk: TerrainChunk) -> None: ...

    def apply_balancing_adjustments(self, chunk: TerrainChunk) -> None: ...

    def on_chunk_unloaded(self, chunk_coord: ChunkCoord) -> None: ...


@dataclass
class LoadedChunk:
    coord: ChunkCoord
    terrain: TerrainChunk


class ChunkStreamer:
    """Streams chunks in/out around a player position."""

    def __init__(
        self,
        terrain_generator: TerrainGenerator,
        view_distance_chunks: int = 2,
        lifecycle_hooks: Iterable[ChunkLifecycleHook] = (),
    ) -> None:
        self.terrain_generator = terrain_generator
        self.view_distance_chunks = view_distance_chunks
        self.lifecycle_hooks = list(lifecycle_hooks)
        self.loaded_chunks: Dict[ChunkCoord, LoadedChunk] = {}

    def update_player_position(self, world_x: float, world_y: float, chunk_size: int = 16) -> None:
        player_chunk = (int(world_x // chunk_size), int(world_y // chunk_size))
        target = self._chunk_window(player_chunk)
        current: Set[ChunkCoord] = set(self.loaded_chunks.keys())

        to_load = sorted(target - current)
        to_unload = sorted(current - target)

        for coord in to_load:
            self._load_chunk(coord)

        for coord in to_unload:
            self._unload_chunk(coord)

    def _chunk_window(self, center: ChunkCoord) -> Set[ChunkCoord]:
        cx, cy = center
        return {
            (x, y)
            for x in range(cx - self.view_distance_chunks, cx + self.view_distance_chunks + 1)
            for y in range(cy - self.view_distance_chunks, cy + self.view_distance_chunks + 1)
        }

    def _load_chunk(self, coord: ChunkCoord) -> None:
        chunk = self.terrain_generator.generate_chunk(*coord)
        self.loaded_chunks[coord] = LoadedChunk(coord=coord, terrain=chunk)

        for hook in self.lifecycle_hooks:
            hook.on_chunk_loaded(chunk)
            hook.apply_spawn_rules(chunk)
            hook.inject_quests(chunk)
            hook.apply_balancing_adjustments(chunk)

    def _unload_chunk(self, coord: ChunkCoord) -> None:
        self.loaded_chunks.pop(coord, None)
        for hook in self.lifecycle_hooks:
            hook.on_chunk_unloaded(coord)
