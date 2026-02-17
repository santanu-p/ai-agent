from __future__ import annotations

from game.world.models import Player, World


def render_camera(world: World, player: Player, radius: int = 4) -> str:
    lines: list[str] = []
    min_y = max(0, player.position.y - radius)
    max_y = min(world.height - 1, player.position.y + radius)
    min_x = max(0, player.position.x - radius)
    max_x = min(world.width - 1, player.position.x + radius)

    for y in range(min_y, max_y + 1):
        row: list[str] = []
        for x in range(min_x, max_x + 1):
            if x == player.position.x and y == player.position.y:
                row.append("P")
            else:
                row.append(".")
        lines.append("".join(row))
    return "\n".join(lines)
