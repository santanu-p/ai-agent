from __future__ import annotations

from dataclasses import dataclass, field
from math import copysign

from engine.world_state import Entity, WorldState


@dataclass
class NPC:
    npc_id: str
    goal: tuple[int, int]
    schedule_hour: int = 8


@dataclass
class NPCSystem:
    world: WorldState
    npcs: dict[str, NPC] = field(default_factory=dict)

    def add_npc(self, npc_id: str, name: str, x: int, y: int, goal: tuple[int, int], schedule_hour: int = 8) -> None:
        self.world.add_entity(Entity(entity_id=npc_id, name=name, x=x, y=y))
        self.npcs[npc_id] = NPC(npc_id=npc_id, goal=goal, schedule_hour=schedule_hour)

    def _next_step(self, current: tuple[int, int], goal: tuple[int, int]) -> tuple[int, int]:
        cx, cy = current
        gx, gy = goal
        if cx != gx:
            cx += int(copysign(1, gx - cx))
        elif cy != gy:
            cy += int(copysign(1, gy - cy))
        return cx, cy

    def update(self, world: WorldState, _: int) -> None:
        current_hour = world.time_of_day.hour
        for npc in sorted(self.npcs.values(), key=lambda n: n.npc_id):
            if current_hour < npc.schedule_hour:
                continue
            entity = world.entities[npc.npc_id]
            nx, ny = self._next_step((entity.x, entity.y), npc.goal)
            entity.x, entity.y = nx, ny
            world.get_chunk_at(nx, ny)
