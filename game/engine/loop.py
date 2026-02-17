from __future__ import annotations

from pathlib import Path
from typing import Iterable

from game.ai.controllers import KeyboardAgentController, SimpleSelfImprovementPipeline
from game.systems.save_system import load_game, save_game
from game.ui.camera import render_camera
from game.world.generator import FlatWorldGenerator
from game.world.models import Player, Position


def run_game_loop(save_path: Path = Path("savegame.json"), command_script: Iterable[str] | None = None) -> None:
    world_generator = FlatWorldGenerator()
    controller = KeyboardAgentController()
    learning = SimpleSelfImprovementPipeline()

    if save_path.exists():
        world, player = load_game(save_path)
        print(f"Loaded world '{world.name}' from {save_path}.")
    else:
        world = world_generator.generate(name="sandbox", seed=42)
        player = Player(name="player-1", position=Position(x=world.width // 2, y=world.height // 2))
        print(f"World '{world.name}' loaded. Player spawned at ({player.position.x}, {player.position.y}).")

    print("Commands: w/a/s/d move, save, load, quit")

    scripted_commands = iter(command_script) if command_script is not None else None

    while True:
        print("\nCamera view:")
        print(render_camera(world, player))
        if scripted_commands is None:
            command = input("> ").strip().lower()
        else:
            try:
                command = next(scripted_commands).strip().lower()
                print(f"> {command}")
            except StopIteration:
                print("Command script exhausted. Exiting sandbox.")
                break

        if command == "quit":
            print("Exiting sandbox.")
            break
        if command == "save":
            save_game(world, player, save_path)
            print(f"Saved to {save_path}.")
            continue
        if command == "load":
            if save_path.exists():
                world, player = load_game(save_path)
                print(f"Loaded from {save_path}.")
            else:
                print("No save file found.")
            continue

        dx, dy = controller.decide(player, world, command)
        player.position.move(dx, dy)
        world.clamp(player.position)
        learning.record_tick(command, (player.position.x, player.position.y))
        learning.run_cycle()
        print(f"Player at ({player.position.x}, {player.position.y})")
