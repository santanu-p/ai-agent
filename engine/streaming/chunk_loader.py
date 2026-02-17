"""Runtime demand-based chunk streaming around active players."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, Set, Tuple


ChunkCoord = Tuple[int, int]
PlayerPosition = Tuple[float, float]


@dataclass(frozen=True)
class ChunkDelta:
    loaded: Set[ChunkCoord]
    unloaded: Set[ChunkCoord]


@dataclass
class LoadedChunk:
    data: object
    last_demand_tick: int


class ChunkLoader:
    """Loads/unloads chunks based on player demand with deterministic chunk coordinates."""

    def __init__(
        self,
        chunk_size: int,
        view_distance: int,
        load_chunk: Callable[[int, int], object],
        unload_chunk: Optional[Callable[[int, int, object], None]] = None,
        unload_grace_ticks: int = 2,
    ):
        self.chunk_size = chunk_size
        self.view_distance = view_distance
        self.load_chunk = load_chunk
        self.unload_chunk = unload_chunk
        self.unload_grace_ticks = unload_grace_ticks
        self._tick = 0
        self._loaded: Dict[ChunkCoord, LoadedChunk] = {}

    def update(self, active_players: Dict[str, PlayerPosition]) -> ChunkDelta:
        self._tick += 1
        demanded = self._demanded_chunks(active_players.values())
        loaded_now: Set[ChunkCoord] = set()
        unloaded_now: Set[ChunkCoord] = set()

        for coord in demanded:
            if coord not in self._loaded:
                self._loaded[coord] = LoadedChunk(data=self.load_chunk(*coord), last_demand_tick=self._tick)
                loaded_now.add(coord)
            else:
                self._loaded[coord].last_demand_tick = self._tick

        for coord, loaded in list(self._loaded.items()):
            if coord in demanded:
                continue
            if self._tick - loaded.last_demand_tick < self.unload_grace_ticks:
                continue
            if self.unload_chunk is not None:
                self.unload_chunk(coord[0], coord[1], loaded.data)
            del self._loaded[coord]
            unloaded_now.add(coord)

        return ChunkDelta(loaded=loaded_now, unloaded=unloaded_now)

    def current_chunks(self) -> Set[ChunkCoord]:
        return set(self._loaded)

    def _demanded_chunks(self, players: Iterable[PlayerPosition]) -> Set[ChunkCoord]:
        demanded: Set[ChunkCoord] = set()
        for x, y in players:
            cx = int(x // self.chunk_size)
            cy = int(y // self.chunk_size)
            for dx in range(-self.view_distance, self.view_distance + 1):
                for dy in range(-self.view_distance, self.view_distance + 1):
                    demanded.add((cx + dx, cy + dy))
        return demanded
