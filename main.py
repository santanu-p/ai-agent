from __future__ import annotations

from pathlib import Path

from game.engine.loop import run_game_loop


if __name__ == "__main__":
    run_game_loop(save_path=Path("savegame.json"))
