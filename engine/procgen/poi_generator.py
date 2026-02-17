"""Deterministic generation of points-of-interest and connective roads."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import heapq
import random
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from engine.procgen.terrain import Biome, GenerationKey, Tile, is_land, neighbors4


class POIType(str, Enum):
    SETTLEMENT = "settlement"
    RUIN = "ruin"
    DUNGEON = "dungeon"


@dataclass(frozen=True)
class POI:
    id: str
    type: POIType
    x: int
    y: int
    chunk_x: int
    chunk_y: int
    metadata: Dict[str, str]


@dataclass(frozen=True)
class Road:
    from_poi: str
    to_poi: str
    path: List[Tuple[int, int]]


class POIGenerator:
    """Builds in-chunk POIs and local roads with seed/version determinism."""

    def __init__(self, key: GenerationKey) -> None:
        self._key = key

    def generate(
        self,
        chunk_x: int,
        chunk_y: int,
        chunk: Sequence[Sequence[Tile]],
        neighboring_pois: Optional[Iterable[POI]] = None,
    ) -> Tuple[List[POI], List[Road]]:
        rng = random.Random(self._key.namespaced_seed(f"poi:{chunk_x}:{chunk_y}"))
        walkable = [tile for row in chunk for tile in row if is_land(tile)]
        if not walkable:
            return [], []

        pois: List[POI] = []
        pois.extend(self._spawn_settlements(chunk_x, chunk_y, walkable, rng))
        pois.extend(self._spawn_ruins(chunk_x, chunk_y, walkable, rng))
        pois.extend(self._spawn_dungeons(chunk_x, chunk_y, walkable, rng))

        connected = list(neighboring_pois or []) + pois
        roads = self._connect_settlements(chunk, connected)
        return pois, roads

    def _spawn_settlements(
        self, chunk_x: int, chunk_y: int, walkable: List[Tile], rng: random.Random
    ) -> List[POI]:
        fertile = [t for t in walkable if t.biome in {Biome.PLAINS, Biome.FOREST, Biome.SAVANNA}]
        count = 1 if fertile and rng.random() < 0.65 else 0
        result: List[POI] = []
        for idx in range(count):
            tile = rng.choice(fertile)
            result.append(
                POI(
                    id=f"settlement:{chunk_x}:{chunk_y}:{idx}",
                    type=POIType.SETTLEMENT,
                    x=tile.x,
                    y=tile.y,
                    chunk_x=chunk_x,
                    chunk_y=chunk_y,
                    metadata={"size": rng.choice(["hamlet", "village", "town"])},
                )
            )
        return result

    def _spawn_ruins(self, chunk_x: int, chunk_y: int, walkable: List[Tile], rng: random.Random) -> List[POI]:
        count = 1 if rng.random() < 0.35 else 0
        if not count:
            return []
        tile = rng.choice(walkable)
        return [
            POI(
                id=f"ruin:{chunk_x}:{chunk_y}:0",
                type=POIType.RUIN,
                x=tile.x,
                y=tile.y,
                chunk_x=chunk_x,
                chunk_y=chunk_y,
                metadata={"age": rng.choice(["ancient", "forgotten", "collapsed"])},
            )
        ]

    def _spawn_dungeons(
        self, chunk_x: int, chunk_y: int, walkable: List[Tile], rng: random.Random
    ) -> List[POI]:
        mountainous = [t for t in walkable if t.biome in {Biome.MOUNTAIN, Biome.TUNDRA, Biome.SNOW}]
        if not mountainous or rng.random() >= 0.45:
            return []
        tile = rng.choice(mountainous)
        return [
            POI(
                id=f"dungeon:{chunk_x}:{chunk_y}:0",
                type=POIType.DUNGEON,
                x=tile.x,
                y=tile.y,
                chunk_x=chunk_x,
                chunk_y=chunk_y,
                metadata={"threat": rng.choice(["low", "medium", "high"])},
            )
        ]

    def _connect_settlements(self, chunk: Sequence[Sequence[Tile]], pois: Sequence[POI]) -> List[Road]:
        settlements = [p for p in pois if p.type == POIType.SETTLEMENT]
        if len(settlements) < 2:
            return []

        roads: List[Road] = []
        for origin in settlements:
            target = min(
                (s for s in settlements if s.id != origin.id),
                key=lambda s: abs(s.x - origin.x) + abs(s.y - origin.y),
            )
            path = self._pathfind(origin, target, chunk)
            if path:
                roads.append(Road(from_poi=origin.id, to_poi=target.id, path=path))
        return roads

    def _pathfind(
        self,
        origin: POI,
        target: POI,
        chunk: Sequence[Sequence[Tile]],
    ) -> List[Tuple[int, int]]:
        tile_map = {(tile.x, tile.y): tile for row in chunk for tile in row}
        start = (origin.x, origin.y)
        goal = (target.x, target.y)
        if start not in tile_map or goal not in tile_map:
            return []

        frontier: List[Tuple[float, Tuple[int, int]]] = [(0.0, start)]
        came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
        cost_so_far: Dict[Tuple[int, int], float] = {start: 0.0}

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal:
                break

            for nxt in neighbors4(*current):
                tile = tile_map.get(nxt)
                if tile is None or not is_land(tile):
                    continue
                move_cost = 1.0 + max(0.0, tile.elevation - 0.7) * 4.0
                new_cost = cost_so_far[current] + move_cost
                if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                    cost_so_far[nxt] = new_cost
                    priority = new_cost + abs(goal[0] - nxt[0]) + abs(goal[1] - nxt[1])
                    heapq.heappush(frontier, (priority, nxt))
                    came_from[nxt] = current

        if goal not in came_from:
            return []

        path: List[Tuple[int, int]] = []
        cur: Optional[Tuple[int, int]] = goal
        while cur is not None:
            path.append(cur)
            cur = came_from[cur]
        path.reverse()
        return path
