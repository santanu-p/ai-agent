from __future__ import annotations

from game.world.interfaces import IWorldGenerator
from game.world.models import World


class FlatWorldGenerator(IWorldGenerator):
    def generate(self, name: str, seed: int) -> World:
        # Minimal world setup for a single-player sandbox.
        return World(name=name, seed=seed, width=20, height=20)
