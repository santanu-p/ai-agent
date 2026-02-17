"""World simulation modules for deterministic generation and streaming."""

from .chunk_streamer import ChunkLifecycleHook, ChunkStreamer
from .entity_registry import EntityRecord, EntityRegistry, EntityType
from .terrain_generator import TerrainChunk, TerrainGenerator
from .world_state_store import ChunkPatch, WorldStateStore

__all__ = [
    "ChunkLifecycleHook",
    "ChunkStreamer",
    "ChunkPatch",
    "EntityRecord",
    "EntityRegistry",
    "EntityType",
    "TerrainChunk",
    "TerrainGenerator",
    "WorldStateStore",
]
