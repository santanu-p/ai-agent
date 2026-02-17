"""World simulation modules.

Includes deterministic terrain generation, chunk streaming, entity registry, and
persistent chunk-local patch storage for reproducible world states.
"""

from .chunk_streamer import ChunkLifecycleHook, ChunkStreamer, LoadedChunk
from .entity_registry import ChunkEntities, EntityRegistry, SpawnRule
from .terrain_generator import TerrainChunk, TerrainGenerator
from .world_state_store import ChunkPatch, WorldStateStore

__all__ = [
    "ChunkLifecycleHook",
    "ChunkStreamer",
    "LoadedChunk",
    "ChunkEntities",
    "EntityRegistry",
    "SpawnRule",
    "TerrainChunk",
    "TerrainGenerator",
    "ChunkPatch",
    "WorldStateStore",
]
