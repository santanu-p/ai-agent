from __future__ import annotations

import argparse
from pathlib import Path

from game.engine.loop import run_game_loop


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the AegisWorld sandbox loop")
    parser.add_argument(
        "--save-path",
        type=Path,
        default=Path("savegame.json"),
        help="Save file path for world persistence (default: savegame.json)",
    )
    parser.add_argument(
        "--colab",
        action="store_true",
        help="Run with scripted commands for notebook environments like Google Colab",
    )
    parser.add_argument(
        "--commands",
        default="d,d,s,a,quit",
        help=(
            "Comma-separated commands used when --colab is enabled "
            "(example: w,d,save,quit)"
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    command_script = [cmd.strip() for cmd in args.commands.split(",") if cmd.strip()] if args.colab else None
    run_game_loop(save_path=args.save_path, command_script=command_script)
