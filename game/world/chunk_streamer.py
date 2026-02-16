from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .entity_registry import ChunkEntities, EntityRegistry
from .terrain_generator import TerrainChunk, TerrainGenerator
from .world_state_store import ChunkCoord, WorldStateStore


class ChunkLifecycleHook(Protocol):
    def on_chunk_pre_load(self, chunk: ChunkCoord) -> None: ...

    def on_chunk_loaded(self, chunk: TerrainChunk, entities: ChunkEntities) -> None: ...

    def on_chunk_pre_unload(self, chunk: ChunkCoord) -> None: ...

    def on_chunk_unloaded(self, chunk: ChunkCoord) -> None: ...


@dataclass
class LoadedChunk:
    terrain: TerrainChunk
    entities: ChunkEntities


class ChunkStreamer:
    """Loads/unloads chunks from player position with lifecycle hooks for AI systems."""

    def __init__(
        self,
        terrain_generator: TerrainGenerator,
        entity_registry: EntityRegistry,
        state_store: WorldStateStore,
        view_distance: int = 2,
    ):
        self.terrain_generator = terrain_generator
        self.entity_registry = entity_registry
        self.state_store = state_store
        self.view_distance = view_distance
        self.loaded_chunks: dict[ChunkCoord, LoadedChunk] = {}
        self.hooks: list[ChunkLifecycleHook] = []

    def register_hook(self, hook: ChunkLifecycleHook) -> None:
        self.hooks.append(hook)

    def update_player_position(self, player_x: int, player_y: int, chunk_size: int = 16) -> None:
        center = (player_x // chunk_size, player_y // chunk_size)
        wanted = self._visible_chunks(center)
        loaded = set(self.loaded_chunks.keys())

        to_unload = loaded - wanted
        to_load = wanted - loaded

        for chunk in sorted(to_unload):
            self._unload_chunk(chunk)

        for chunk in sorted(to_load):
            self._load_chunk(chunk)

    def _visible_chunks(self, center: ChunkCoord) -> set[ChunkCoord]:
        cx, cy = center
        result: set[ChunkCoord] = set()
        for x in range(cx - self.view_distance, cx + self.view_distance + 1):
            for y in range(cy - self.view_distance, cy + self.view_distance + 1):
                result.add((x, y))
        return result

    def _load_chunk(self, chunk: ChunkCoord) -> None:
        for hook in self.hooks:
            hook.on_chunk_pre_load(chunk)

        terrain = self.terrain_generator.generate_chunk(chunk)
        entities = self.entity_registry.populate_chunk(terrain)

        self.loaded_chunks[chunk] = LoadedChunk(terrain=terrain, entities=entities)

        for hook in self.hooks:
            hook.on_chunk_loaded(terrain, entities)

    def _unload_chunk(self, chunk: ChunkCoord) -> None:
        for hook in self.hooks:
            hook.on_chunk_pre_unload(chunk)

        self.state_store.append_patch(
            chunk=chunk,
            operations=[{"op": "chunk_unloaded", "reason": "streaming_out"}],
            author_system="chunk_streamer",
            tags=("lifecycle",),
        )
        self.loaded_chunks.pop(chunk, None)

        for hook in self.hooks:
            hook.on_chunk_unloaded(chunk)
