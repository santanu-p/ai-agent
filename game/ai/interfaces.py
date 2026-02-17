from __future__ import annotations

from abc import ABC, abstractmethod

from game.world.models import Player, World


class IAgentController(ABC):
    @abstractmethod
    def decide(self, player: Player, world: World, raw_input: str) -> tuple[int, int]:
        """Translate input/strategy into a movement vector."""


class ISelfImprovementPipeline(ABC):
    @abstractmethod
    def record_tick(self, command: str, position: tuple[int, int]) -> None:
        """Record a tick for future learning."""

    @abstractmethod
    def run_cycle(self) -> None:
        """Execute a minimal improvement cycle."""
