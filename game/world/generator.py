from __future__ import annotations

import random
from typing import Any, Dict

from game.engine.interfaces import IWorldGenerator


class FlatWorldGenerator(IWorldGenerator):
    """Creates a tiny flat map for local sandbox play."""

    def __init__(self, width: int = 12, height: int = 8) -> None:
        self.width = width
        self.height = height

    def generate(self, seed: int | None = None) -> Dict[str, Any]:
        rng = random.Random(seed)
        tiles = [["." for _ in range(self.width)] for _ in range(self.height)]

        # Sprinkle simple obstacles.
        obstacle_count = max(1, (self.width * self.height) // 12)
        for _ in range(obstacle_count):
            x = rng.randrange(self.width)
            y = rng.randrange(self.height)
            tiles[y][x] = "#"

        return {
            "name": "sandbox",
            "size": {"width": self.width, "height": self.height},
            "tiles": tiles,
        }
