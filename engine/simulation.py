"""Fixed-step deterministic simulation loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

from engine.world_state import WorldState

SystemFn = Callable[[WorldState, int], None]


@dataclass
class Simulation:
    world: WorldState
    fixed_step_ms: int = 50
    systems: List[SystemFn] = field(default_factory=list)

    def register_system(self, system: SystemFn) -> None:
        self.systems.append(system)

    def tick_once(self) -> None:
        next_tick = self.world.tick + 1
        for system in self.systems:
            system(self.world, next_tick)
        self.world.tick = next_tick
        self.world.time_of_day.advance(1)

    def run_steps(self, steps: int) -> None:
        for _ in range(steps):
            self.tick_once()
