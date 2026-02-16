"""Launch entrypoint for the minimal game runtime."""

from __future__ import annotations

from engine.simulation import Simulation
from engine.world_state import WorldState
from game.npc_system import Goal, NPCSystem
from game.player_controller import PlayerController


def main() -> None:
    world = WorldState(world_seed=12345)
    player_controller = PlayerController(player_id="player-1")
    player_controller.ensure_player(world, spawn=(0, 0))

    npc_system = NPCSystem()
    npc_system.add_npc(world, "npc-1", (5, 5))
    npc_system.set_schedule(
        "npc-1",
        {
            1: Goal(kind="work", target_position=(8, 8)),
            50: Goal(kind="rest", target_position=(2, 2)),
        },
    )

    sim = Simulation(world=world)
    sim.register_system(npc_system.update)

    print(f"Booting world seed={world.world_seed} with player at {world.entities['player-1'].position}")
    for _ in range(10):
        sim.tick_once()
        print(f"tick={world.tick} time={world.time_of_day.day}:{world.time_of_day.tick_of_day} npc={world.entities['npc-1'].position}")


if __name__ == "__main__":
    main()
