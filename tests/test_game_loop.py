from pathlib import Path

from game.engine.loop import run_game_loop


def test_game_loop_supports_scripted_commands_for_notebooks(tmp_path: Path) -> None:
    save_path = tmp_path / "colab-save.json"

    run_game_loop(save_path=save_path, command_script=["d", "save", "quit"])

    assert save_path.exists()
