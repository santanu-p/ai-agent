from __future__ import annotations

from game.ai.interfaces import IAgentController, ISelfImprovementPipeline
from game.world.models import Player, World


class KeyboardAgentController(IAgentController):
    MOVE_MAP = {
        "w": (0, -1),
        "a": (-1, 0),
        "s": (0, 1),
        "d": (1, 0),
    }

    def decide(self, player: Player, world: World, raw_input: str) -> tuple[int, int]:
        return self.MOVE_MAP.get(raw_input.lower().strip(), (0, 0))


class SimpleSelfImprovementPipeline(ISelfImprovementPipeline):
    def __init__(self) -> None:
        self.ticks: list[tuple[str, tuple[int, int]]] = []

    def record_tick(self, command: str, position: tuple[int, int]) -> None:
        self.ticks.append((command, position))

    def run_cycle(self) -> None:
        # Placeholder: in future this could adjust policies from tick history.
        if len(self.ticks) > 500:
            self.ticks = self.ticks[-200:]
