from __future__ import annotations

from typing import Any, Dict


class ConsoleRenderer:
    def draw(self, world_state: Dict[str, Any]) -> None:
        tiles = [row[:] for row in world_state["world"]["tiles"]]
        px = world_state["player"]["x"]
        py = world_state["player"]["y"]
        cx = world_state["camera"]["x"]
        cy = world_state["camera"]["y"]

        tiles[py][px] = "P"

        print("\n=== Sandbox World ===")
        print(f"Player: ({px}, {py}) | Camera: ({cx}, {cy})")
        for row in tiles:
            print(" ".join(row))
