from __future__ import annotations

from abc import ABC, abstractmethod

from game.world.models import World


class IWorldGenerator(ABC):
    @abstractmethod
    def generate(self, name: str, seed: int) -> World:
        """Generate and return a new world."""
