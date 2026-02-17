"""Deterministic terrain generation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from random import Random
from typing import List


@dataclass(frozen=True)
class TerrainChunk:
    """Output structure for generated terrain."""

    chunk_x: int
    chunk_y: int
    size: int
    height_map: List[List[float]]
    biome_map: List[List[str]]
    seed_material: str


class TerrainGenerator:
    """Seed-based deterministic chunk terrain generation.

    Determinism strategy:
    - All chunk seeds are derived from (world_seed, generation_epoch, chunk_x, chunk_y)
    - A cryptographic hash (BLAKE2b) converts seed material to an integer RNG seed
    - The same inputs always produce identical chunk output across clients/saves
    """

    def __init__(self, world_seed: str, generation_epoch: int = 0) -> None:
        self.world_seed = world_seed
        self.generation_epoch = generation_epoch

    def derive_chunk_seed(self, chunk_x: int, chunk_y: int) -> int:
        material = self._seed_material(chunk_x, chunk_y)
        digest = blake2b(material.encode("utf-8"), digest_size=16).hexdigest()
        return int(digest, 16)

    def generate_chunk(self, chunk_x: int, chunk_y: int, size: int = 16) -> TerrainChunk:
        material = self._seed_material(chunk_x, chunk_y)
        rng = Random(self.derive_chunk_seed(chunk_x, chunk_y))

        height_map: List[List[float]] = []
        biome_map: List[List[str]] = []

        for _row in range(size):
            heights = [round(rng.uniform(0.0, 1.0), 4) for _ in range(size)]
            biomes = [self._biome_for_height(height) for height in heights]
            height_map.append(heights)
            biome_map.append(biomes)

        return TerrainChunk(
            chunk_x=chunk_x,
            chunk_y=chunk_y,
            size=size,
            height_map=height_map,
            biome_map=biome_map,
            seed_material=material,
        )

    def _seed_material(self, chunk_x: int, chunk_y: int) -> str:
        return f"{self.world_seed}:{self.generation_epoch}:{chunk_x}:{chunk_y}"

    @staticmethod
    def _biome_for_height(height: float) -> str:
        if height < 0.2:
            return "water"
        if height < 0.4:
            return "shore"
        if height < 0.7:
            return "plains"
        if height < 0.9:
            return "forest"
        return "mountain"
