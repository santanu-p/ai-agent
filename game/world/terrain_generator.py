from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random
from typing import Any

from .world_state_store import ChunkCoord, WorldStateStore


@dataclass(frozen=True)
class TerrainChunk:
    chunk: ChunkCoord
    biome: str
    elevation: list[list[float]]
    humidity: list[list[float]]
    temperature: list[list[float]]
    patch_ops: list[dict[str, Any]]


class TerrainGenerator:
    """Seed-based deterministic terrain generation.

    Every chunk derives a local RNG stream from world seed + chunk coordinate to ensure
    all clients produce identical base maps before patch replay.
    """

    def __init__(self, world_seed: str, state_store: WorldStateStore, tile_size: int = 16):
        self.world_seed = world_seed
        self.state_store = state_store
        self.tile_size = tile_size

    def _chunk_rng(self, chunk: ChunkCoord) -> random.Random:
        payload = f"{self.world_seed}:{chunk[0]}:{chunk[1]}".encode("utf-8")
        seed = int(hashlib.blake2b(payload, digest_size=16).hexdigest(), 16)
        return random.Random(seed)

    def _sample_grid(self, rng: random.Random, offset: float = 0.0) -> list[list[float]]:
        return [
            [round(min(1.0, max(0.0, rng.random() + offset)), 4) for _ in range(self.tile_size)]
            for _ in range(self.tile_size)
        ]

    def generate_chunk(self, chunk: ChunkCoord) -> TerrainChunk:
        rng = self._chunk_rng(chunk)
        elevation = self._sample_grid(rng)
        humidity = self._sample_grid(rng, offset=-0.1)
        temperature = self._sample_grid(rng, offset=0.1)

        biome = self._classify_biome(elevation, humidity, temperature)
        patch_ops = self.state_store.materialize_chunk_state(chunk)["ops"]

        return TerrainChunk(
            chunk=chunk,
            biome=biome,
            elevation=elevation,
            humidity=humidity,
            temperature=temperature,
            patch_ops=patch_ops,
        )

    def _classify_biome(
        self,
        elevation: list[list[float]],
        humidity: list[list[float]],
        temperature: list[list[float]],
    ) -> str:
        avg_elevation = sum(sum(row) for row in elevation) / (self.tile_size**2)
        avg_humidity = sum(sum(row) for row in humidity) / (self.tile_size**2)
        avg_temp = sum(sum(row) for row in temperature) / (self.tile_size**2)

        if avg_elevation > 0.75:
            return "mountain"
        if avg_temp > 0.7 and avg_humidity < 0.35:
            return "desert"
        if avg_humidity > 0.65:
            return "wetlands"
        return "plains"
