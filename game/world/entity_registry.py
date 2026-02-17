from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import random
from typing import TYPE_CHECKING, Any

from .world_state_store import ChunkCoord

if TYPE_CHECKING:
    from .terrain_generator import TerrainChunk


@dataclass(frozen=True)
class SpawnRule:
    entity_type: str
    min_count: int
    max_count: int
    biome_allowlist: tuple[str, ...]
    tags: tuple[str, ...] = ()


@dataclass
class ChunkEntities:
    chunk: ChunkCoord
    entities: list[dict[str, Any]] = field(default_factory=list)


class EntityRegistry:
    """Registry for NPCs, fauna, and gatherable resources."""

    def __init__(self, world_seed: str):
        self.world_seed = world_seed
        self.spawn_rules: list[SpawnRule] = [
            SpawnRule("npc.villager", 1, 4, ("plains", "wetlands"), ("quest_giver",)),
            SpawnRule("fauna.deer", 2, 8, ("plains", "wetlands")),
            SpawnRule("fauna.sand_worm", 1, 3, ("desert",), ("hostile",)),
            SpawnRule("resource.iron_vein", 1, 5, ("mountain", "plains"), ("mining",)),
            SpawnRule("resource.herb_patch", 2, 6, ("wetlands", "plains"), ("alchemy",)),
        ]

    def _chunk_rng(self, chunk: ChunkCoord) -> random.Random:
        payload = f"entity:{self.world_seed}:{chunk[0]}:{chunk[1]}".encode("utf-8")
        seed = int(hashlib.sha256(payload).hexdigest(), 16)
        return random.Random(seed)

    def populate_chunk(self, terrain_chunk: TerrainChunk) -> ChunkEntities:
        rng = self._chunk_rng(terrain_chunk.chunk)
        entities: list[dict[str, Any]] = []

        for rule in self.spawn_rules:
            if terrain_chunk.biome not in rule.biome_allowlist:
                continue

            count = rng.randint(rule.min_count, rule.max_count)
            for idx in range(count):
                entities.append(
                    {
                        "entity_id": self._entity_id(terrain_chunk.chunk, rule.entity_type, idx),
                        "entity_type": rule.entity_type,
                        "tags": list(rule.tags),
                        "position": {
                            "x": rng.randint(0, 15),
                            "y": rng.randint(0, 15),
                        },
                    }
                )

        return ChunkEntities(chunk=terrain_chunk.chunk, entities=entities)

    def _entity_id(self, chunk: ChunkCoord, entity_type: str, ordinal: int) -> str:
        payload = f"{self.world_seed}:{chunk}:{entity_type}:{ordinal}".encode("utf-8")
        return hashlib.blake2s(payload, digest_size=10).hexdigest()

    def apply_balancing_adjustments(
        self, entities: ChunkEntities, adjustments: list[dict[str, Any]]
    ) -> ChunkEntities:
        """Applies dynamic balancing patches produced by AI systems."""
        by_type: dict[str, int] = {}
        for entry in entities.entities:
            by_type[entry["entity_type"]] = by_type.get(entry["entity_type"], 0) + 1

        for adjustment in adjustments:
            entity_type = adjustment["entity_type"]
            delta = int(adjustment.get("delta", 0))
            by_type[entity_type] = max(0, by_type.get(entity_type, 0) + delta)

        updated_entities: list[dict[str, Any]] = []
        rng = self._chunk_rng(entities.chunk)
        for entity_type, count in by_type.items():
            for idx in range(count):
                updated_entities.append(
                    {
                        "entity_id": self._entity_id(entities.chunk, entity_type, idx),
                        "entity_type": entity_type,
                        "tags": [],
                        "position": {"x": rng.randint(0, 15), "y": rng.randint(0, 15)},
                    }
                )

        return ChunkEntities(chunk=entities.chunk, entities=updated_entities)
