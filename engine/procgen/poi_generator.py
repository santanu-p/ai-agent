"""Procedural POI generation tied to deterministic terrain chunks."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
import random
from typing import Dict, Iterable, List, Tuple

from engine.procgen.terrain import TerrainChunk


Coord = Tuple[int, int]


@dataclass(frozen=True)
class PointOfInterest:
    poi_id: str
    kind: str
    position: Coord
    metadata: Dict[str, str]


@dataclass(frozen=True)
class Road:
    start_poi: str
    end_poi: str
    path: List[Coord]


@dataclass(frozen=True)
class ChunkPOIResult:
    chunk_x: int
    chunk_y: int
    seed: int
    version: str
    points: List[PointOfInterest]
    roads: List[Road]


class POIGenerator:
    """Creates settlements, ruins, dungeons, and roads for each chunk."""

    def __init__(self, seed: int, version: str):
        self.seed = seed
        self.version = version

    def generate_chunk_pois(self, terrain_chunk: TerrainChunk) -> ChunkPOIResult:
        rng = self._chunk_rng(terrain_chunk.chunk_x, terrain_chunk.chunk_y)
        points: List[PointOfInterest] = []

        for y, row in enumerate(terrain_chunk.cells):
            for x, cell in enumerate(row):
                world_pos = (
                    terrain_chunk.chunk_x * len(row) + x,
                    terrain_chunk.chunk_y * len(terrain_chunk.cells) + y,
                )
                roll = rng.random()
                if cell.biome in {"grassland", "temperate_forest"} and roll < 0.012:
                    points.append(self._poi("settlement", world_pos, rng, prosperity=cell.moisture))
                elif cell.biome in {"desert", "mountain", "taiga"} and roll < 0.009:
                    points.append(self._poi("ruin", world_pos, rng, age=cell.elevation))
                elif cell.biome not in {"ocean"} and roll < 0.008:
                    points.append(self._poi("dungeon", world_pos, rng, danger=cell.elevation + cell.moisture))

        roads = self._generate_roads(points)
        return ChunkPOIResult(
            chunk_x=terrain_chunk.chunk_x,
            chunk_y=terrain_chunk.chunk_y,
            seed=self.seed,
            version=self.version,
            points=points,
            roads=roads,
        )

    def _generate_roads(self, points: Iterable[PointOfInterest]) -> List[Road]:
        settlements = [p for p in points if p.kind == "settlement"]
        roads: List[Road] = []
        for i, source in enumerate(settlements):
            nearest = self._nearest(source.position, settlements[:i] + settlements[i + 1 :])
            if not nearest:
                continue
            start, end = source.position, nearest.position
            road = Road(start_poi=source.poi_id, end_poi=nearest.poi_id, path=self._manhattan_path(start, end))
            if road.start_poi < road.end_poi:
                roads.append(road)
        return roads

    @staticmethod
    def _nearest(position: Coord, candidates: List[PointOfInterest]) -> PointOfInterest | None:
        if not candidates:
            return None
        return min(candidates, key=lambda poi: abs(position[0] - poi.position[0]) + abs(position[1] - poi.position[1]))

    @staticmethod
    def _manhattan_path(start: Coord, end: Coord) -> List[Coord]:
        x0, y0 = start
        x1, y1 = end
        path = [start]

        step_x = 1 if x1 > x0 else -1
        for x in range(x0, x1, step_x):
            path.append((x + step_x, y0))

        step_y = 1 if y1 > y0 else -1
        for y in range(y0, y1, step_y):
            path.append((x1, y + step_y))

        return path

    def _poi(self, kind: str, position: Coord, rng: random.Random, **metrics: float) -> PointOfInterest:
        digest = blake2b(
            f"poi:{self.seed}:{self.version}:{kind}:{position[0]}:{position[1]}".encode(),
            digest_size=6,
        ).hexdigest()
        poi_id = f"{kind[:3]}-{digest}"
        metadata = {k: f"{v:.2f}" for k, v in metrics.items()}
        metadata["name_seed"] = str(rng.randint(1000, 9999))
        return PointOfInterest(poi_id=poi_id, kind=kind, position=position, metadata=metadata)

    def _chunk_rng(self, chunk_x: int, chunk_y: int) -> random.Random:
        digest = blake2b(
            f"poi-chunk:{self.seed}:{self.version}:{chunk_x}:{chunk_y}".encode(),
            digest_size=16,
        ).digest()
        return random.Random(int.from_bytes(digest, "big"))
