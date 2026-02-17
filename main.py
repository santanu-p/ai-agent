from __future__ import annotations

from engine.persistence import save_snapshot
from engine.simulation import Simulation
from engine.world_state import WorldState
from game.npc_system import NPCSystem
from game.player_controller import PlayerController


def boot(seed: int = 42) -> tuple[WorldState, Simulation, PlayerController]:
    world = WorldState.bootstrap(seed=seed, chunk_radius=1)
    player = PlayerController.spawn(world, player_id="player", x=0, y=0)

    npc_system = NPCSystem(world=world)
    npc_system.add_npc("npc_1", "Guide", x=2, y=2, goal=(0, 0), schedule_hour=6)

    simulation = Simulation(world=world, fixed_step_ms=100)
    simulation.register_system("npc_system", npc_system.update)

    return world, simulation, player


def run(seed: int = 42, steps: int = 5) -> None:
    world, simulation, player = boot(seed=seed)
    for _ in range(steps):
        simulation.tick()

    snapshot = save_snapshot(world, "world_snapshot.json")
    print(
        f"Simulation complete: ticks={simulation.tick_count}, player={player.position}, "
        f"time={world.time_of_day.hour:02d}:{world.time_of_day.minute:02d}, snapshot={snapshot}"
    )


if __name__ == "__main__":
    run()
