"""Deterministic terrain and biome generation for chunk-based worlds."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
import math
import random
from typing import List


@dataclass(frozen=True)
class TerrainConfig:
    chunk_size: int = 32
    elevation_scale: float = 96.0
    moisture_scale: float = 72.0
    temperature_scale: float = 128.0
    octaves: int = 4
    persistence: float = 0.5
    lacunarity: float = 2.0
    sea_level: float = 0.42


@dataclass(frozen=True)
class TerrainCell:
    elevation: float
    moisture: float
    temperature: float
    biome: str


@dataclass(frozen=True)
class TerrainChunk:
    chunk_x: int
    chunk_y: int
    seed: int
    version: str
    cells: List[List[TerrainCell]]


class TerrainGenerator:
    """Generates reproducible terrain data from a seed and worldgen version."""

    def __init__(self, seed: int, version: str, config: TerrainConfig | None = None):
        self.seed = seed
        self.version = version
        self.config = config or TerrainConfig()

    def generate_chunk(self, chunk_x: int, chunk_y: int) -> TerrainChunk:
        cells: List[List[TerrainCell]] = []
        for local_y in range(self.config.chunk_size):
            row: List[TerrainCell] = []
            world_y = chunk_y * self.config.chunk_size + local_y
            for local_x in range(self.config.chunk_size):
                world_x = chunk_x * self.config.chunk_size + local_x
                elevation = self._fractal_noise(world_x, world_y, self.config.elevation_scale)
                moisture = self._fractal_noise(world_x, world_y, self.config.moisture_scale)
                latitude = abs(world_y) / (self.config.chunk_size * 128)
                latitude_temp_drop = min(latitude, 1.0) * 0.45
                temperature = self._fractal_noise(world_x, world_y, self.config.temperature_scale) - latitude_temp_drop
                temperature = max(0.0, min(1.0, temperature))
                biome = self._classify_biome(elevation, moisture, temperature)
                row.append(TerrainCell(elevation=elevation, moisture=moisture, temperature=temperature, biome=biome))
            cells.append(row)

        return TerrainChunk(
            chunk_x=chunk_x,
            chunk_y=chunk_y,
            seed=self.seed,
            version=self.version,
            cells=cells,
        )

    def _fractal_noise(self, x: int, y: int, base_scale: float) -> float:
        amplitude = 1.0
        frequency = 1.0 / max(base_scale, 1.0)
        value = 0.0
        amplitude_sum = 0.0

        for octave in range(self.config.octaves):
            sample = self._value_noise(x * frequency, y * frequency, octave)
            value += sample * amplitude
            amplitude_sum += amplitude
            amplitude *= self.config.persistence
            frequency *= self.config.lacunarity

        return value / amplitude_sum if amplitude_sum else 0.0

    def _value_noise(self, x: float, y: float, octave: int) -> float:
        x0 = math.floor(x)
        y0 = math.floor(y)
        x1 = x0 + 1
        y1 = y0 + 1
        sx = x - x0
        sy = y - y0

        n00 = self._lattice(x0, y0, octave)
        n10 = self._lattice(x1, y0, octave)
        n01 = self._lattice(x0, y1, octave)
        n11 = self._lattice(x1, y1, octave)

        ix0 = self._lerp(n00, n10, self._smoothstep(sx))
        ix1 = self._lerp(n01, n11, self._smoothstep(sx))
        return self._lerp(ix0, ix1, self._smoothstep(sy))

    def _lattice(self, x: int, y: int, octave: int) -> float:
        digest = blake2b(
            f"terrain:{self.seed}:{self.version}:{octave}:{x}:{y}".encode(),
            digest_size=16,
        ).digest()
        rng = random.Random(int.from_bytes(digest, "big"))
        return rng.random()

    @staticmethod
    def _smoothstep(t: float) -> float:
        return t * t * (3.0 - 2.0 * t)

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + t * (b - a)

    def _classify_biome(self, elevation: float, moisture: float, temperature: float) -> str:
        if elevation < self.config.sea_level:
            return "ocean"
        if elevation > 0.86:
            return "mountain"
        if temperature < 0.2:
            return "tundra" if moisture < 0.5 else "taiga"
        if moisture < 0.2:
            return "desert"
        if moisture < 0.4:
            return "grassland"
        if moisture < 0.7:
            return "temperate_forest"
        return "rainforest"
