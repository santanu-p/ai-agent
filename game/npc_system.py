"""Autonomous NPC system with goals and simple pathing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from engine.world_state import Entity, WorldState


@dataclass
class Goal:
    kind: str
    target_position: Tuple[int, int]


@dataclass
class NPCProfile:
    entity_id: str
    schedule: Dict[int, Goal] = field(default_factory=dict)


@dataclass
class NPCSystem:
    npcs: Dict[str, NPCProfile] = field(default_factory=dict)

    def add_npc(self, world: WorldState, entity_id: str, position: Tuple[int, int]) -> None:
        if entity_id in world.entities:
            return
        world.add_entity(Entity(entity_id=entity_id, kind="npc", position=position))
        self.npcs[entity_id] = NPCProfile(entity_id=entity_id)

    def set_schedule(self, entity_id: str, schedule: Dict[int, Goal]) -> None:
        if entity_id not in self.npcs:
            self.npcs[entity_id] = NPCProfile(entity_id=entity_id)
        self.npcs[entity_id].schedule = schedule

    def update(self, world: WorldState, tick: int) -> None:
        for entity_id in sorted(self.npcs.keys()):
            npc = world.entities.get(entity_id)
            if not npc:
                continue
            goal = self._goal_for_tick(self.npcs[entity_id], tick)
            if not goal:
                continue
            npc.position = self._step_towards(npc.position, goal.target_position)

    def _goal_for_tick(self, profile: NPCProfile, tick: int) -> Goal | None:
        if not profile.schedule:
            return None

        keys: List[int] = sorted(profile.schedule.keys())
        selected = keys[0]
        for schedule_tick in keys:
            if schedule_tick <= tick:
                selected = schedule_tick
            else:
                break
        return profile.schedule[selected]

    @staticmethod
    def _step_towards(start: Tuple[int, int], target: Tuple[int, int]) -> Tuple[int, int]:
        sx, sy = start
        tx, ty = target
        dx = 0 if sx == tx else (1 if tx > sx else -1)
        dy = 0 if sy == ty else (1 if ty > sy else -1)
        return sx + dx, sy + dy
