from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from game.ai.controller import KeyboardAgentController
from game.ai.improvement import NoOpSelfImprovementPipeline
from game.engine.interfaces import IWorldGenerator
from game.systems.persistence import SaveLoadSystem
from game.ui.render import ConsoleRenderer


@dataclass
class SandboxGame:
    world_generator: IWorldGenerator
    controller: KeyboardAgentController
    renderer: ConsoleRenderer
    persistence: SaveLoadSystem
    self_improvement: NoOpSelfImprovementPipeline

    def _spawn_player(self, world: Dict) -> Dict[str, int]:
        width = world["size"]["width"]
        height = world["size"]["height"]
        return {"x": width // 2, "y": height // 2}

    def _move_player(self, state: Dict, action: str) -> None:
        offsets = {"w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0)}
        if action not in offsets:
            return

        dx, dy = offsets[action]
        width = state["world"]["size"]["width"]
        height = state["world"]["size"]["height"]

        nx = max(0, min(width - 1, state["player"]["x"] + dx))
        ny = max(0, min(height - 1, state["player"]["y"] + dy))

        if state["world"]["tiles"][ny][nx] != "#":
            state["player"]["x"] = nx
            state["player"]["y"] = ny
            state["moves"] += 1

    def _update_camera(self, state: Dict) -> None:
        state["camera"]["x"] = state["player"]["x"]
        state["camera"]["y"] = state["player"]["y"]

    def run(self, seed: int | None = 42) -> None:
        world = self.world_generator.generate(seed=seed)
        state = {
            "world": world,
            "player": self._spawn_player(world),
            "camera": {"x": 0, "y": 0},
            "moves": 0,
        }
        self._update_camera(state)

        print("World loaded. Player spawned. Enter commands to play.")
        running = True
        while running:
            self.renderer.draw(state)
            action = self.controller.next_action(state)

            if action == "quit":
                running = False
            elif action == "save":
                self.persistence.save(state)
                print("Game saved.")
            elif action == "load":
                state = self.persistence.load()
                print("Game loaded.")
            else:
                self._move_player(state, action)
                self._update_camera(state)

        report = self.self_improvement.run_cycle({"moves": state["moves"]})
        print(f"Session ended: {report['note']}")
