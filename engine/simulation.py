from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from engine.world_state import WorldState

SystemFn = Callable[[WorldState, int], None]


@dataclass
class Simulation:
    world: WorldState
    fixed_step_ms: int = 100
    tick_count: int = 0
    _systems: list[tuple[str, SystemFn]] = field(default_factory=list)

    def register_system(self, name: str, system_fn: SystemFn) -> None:
        self._systems.append((name, system_fn))

    @property
    def system_order(self) -> list[str]:
        return [name for name, _ in self._systems]

    def tick(self) -> None:
        self.tick_count += 1
        for _, system in self._systems:
            system(self.world, self.tick_count)
        self.world.step_time(minutes=1)

    def run_steps(self, steps: int) -> None:
        for _ in range(steps):
            self.tick()
