from __future__ import annotations

import json
from pathlib import Path

from game.world.models import Player, World


DEFAULT_SAVE_PATH = Path("savegame.json")


def save_game(world: World, player: Player, path: Path = DEFAULT_SAVE_PATH) -> None:
    payload = {
        "world": world.to_dict(),
        "player": player.to_dict(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_game(path: Path = DEFAULT_SAVE_PATH) -> tuple[World, Player]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    world = World.from_dict(payload["world"])
    player = Player.from_dict(payload["player"])
    return world, player
