"""Procedural terrain and biome generation.

The generator is deterministic for a `(seed, version)` pair so saved chunks can
be reconstructed in future sessions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import math
from typing import Dict, List, Tuple


class Biome(str, Enum):
    OCEAN = "ocean"
    BEACH = "beach"
    PLAINS = "plains"
    FOREST = "forest"
    DESERT = "desert"
    SAVANNA = "savanna"
    TUNDRA = "tundra"
    MOUNTAIN = "mountain"
    SNOW = "snow"
    SWAMP = "swamp"


@dataclass(frozen=True)
class GenerationKey:
    """Reproducibility key used by every world-generation subsystem."""

    seed: int
    version: str

    def namespaced_seed(self, namespace: str) -> int:
        payload = f"{self.seed}:{self.version}:{namespace}".encode("utf-8")
        digest = hashlib.blake2s(payload, digest_size=8).digest()
        return int.from_bytes(digest, "big", signed=False)


@dataclass(frozen=True)
class Tile:
    x: int
    y: int
    elevation: float
    moisture: float
    temperature: float
    biome: Biome


class TerrainGenerator:
    """Generates terrain from fractal value noise and classifies biomes."""

    def __init__(
        self,
        key: GenerationKey,
        base_scale: float = 80.0,
        octaves: int = 5,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
        sea_level: float = 0.42,
    ) -> None:
        self._key = key
        self._seed = key.namespaced_seed("terrain")
        self._moisture_seed = key.namespaced_seed("moisture")
        self._temperature_seed = key.namespaced_seed("temperature")
        self._base_scale = base_scale
        self._octaves = octaves
        self._persistence = persistence
        self._lacunarity = lacunarity
        self._sea_level = sea_level

    def generate_chunk(
        self, chunk_x: int, chunk_y: int, chunk_size: int
    ) -> List[List[Tile]]:
        """Generate a chunk with deterministic terrain and biome assignment."""
        tiles: List[List[Tile]] = []
        origin_x = chunk_x * chunk_size
        origin_y = chunk_y * chunk_size

        for ly in range(chunk_size):
            row: List[Tile] = []
            for lx in range(chunk_size):
                x = origin_x + lx
                y = origin_y + ly
                elevation = self._fbm_noise(x, y, self._seed)
                moisture = self._fbm_noise(x, y, self._moisture_seed)
                latitude = abs((y % 4096) / 4096.0 - 0.5) * 2.0
                climate_band = 1.0 - latitude
                temperature = max(
                    0.0,
                    min(
                        1.0,
                        0.7 * self._fbm_noise(x, y, self._temperature_seed)
                        + 0.3 * climate_band
                        - elevation * 0.2,
                    ),
                )
                biome = self._assign_biome(elevation, moisture, temperature)
                row.append(
                    Tile(
                        x=x,
                        y=y,
                        elevation=elevation,
                        moisture=moisture,
                        temperature=temperature,
                        biome=biome,
                    )
                )
            tiles.append(row)

        return tiles

    def _assign_biome(self, elevation: float, moisture: float, temperature: float) -> Biome:
        if elevation < self._sea_level:
            return Biome.OCEAN
        if elevation < self._sea_level + 0.03:
            return Biome.BEACH
        if elevation > 0.85:
            return Biome.SNOW if temperature < 0.35 else Biome.MOUNTAIN
        if temperature < 0.22:
            return Biome.TUNDRA if moisture < 0.55 else Biome.SNOW
        if temperature > 0.78:
            if moisture < 0.28:
                return Biome.DESERT
            return Biome.SAVANNA if moisture < 0.55 else Biome.SWAMP
        if moisture > 0.72:
            return Biome.SWAMP
        if moisture > 0.45:
            return Biome.FOREST
        return Biome.PLAINS

    def _fbm_noise(self, x: int, y: int, seed: int) -> float:
        total = 0.0
        frequency = 1.0
        amplitude = 1.0
        normalization = 0.0

        for _ in range(self._octaves):
            sample_x = x / self._base_scale * frequency
            sample_y = y / self._base_scale * frequency
            total += self._value_noise(sample_x, sample_y, seed) * amplitude
            normalization += amplitude
            amplitude *= self._persistence
            frequency *= self._lacunarity

        return total / normalization if normalization else 0.0

    def _value_noise(self, x: float, y: float, seed: int) -> float:
        x0 = math.floor(x)
        y0 = math.floor(y)
        x1 = x0 + 1
        y1 = y0 + 1

        sx = self._smoothstep(x - x0)
        sy = self._smoothstep(y - y0)

        n00 = self._grid_random(x0, y0, seed)
        n10 = self._grid_random(x1, y0, seed)
        n01 = self._grid_random(x0, y1, seed)
        n11 = self._grid_random(x1, y1, seed)

        nx0 = self._lerp(n00, n10, sx)
        nx1 = self._lerp(n01, n11, sx)
        return self._lerp(nx0, nx1, sy)

    @staticmethod
    def _smoothstep(t: float) -> float:
        return t * t * (3.0 - 2.0 * t)

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a * (1.0 - t) + b * t

    @staticmethod
    def _grid_random(x: int, y: int, seed: int) -> float:
        payload = f"{seed}:{x}:{y}".encode("utf-8")
        digest = hashlib.blake2b(payload, digest_size=8).digest()
        raw = int.from_bytes(digest, "big", signed=False)
        return raw / ((1 << 64) - 1)


def summarize_chunk_biomes(chunk: List[List[Tile]]) -> Dict[Biome, int]:
    """Convenience helper useful for balancing and telemetry."""
    summary: Dict[Biome, int] = {}
    for row in chunk:
        for tile in row:
            summary[tile.biome] = summary.get(tile.biome, 0) + 1
    return summary


def is_land(tile: Tile) -> bool:
    return tile.biome not in {Biome.OCEAN, Biome.BEACH}


def neighbors4(x: int, y: int) -> Tuple[Tuple[int, int], ...]:
    return ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
