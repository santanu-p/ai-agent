from pathlib import Path

from engine.persistence import load_world, save_world
from engine.simulation import Simulation
from engine.world_state import WorldState
from game.npc_system import Goal, NPCSystem
from game.player_controller import PlayerController


def test_world_initialization_and_player_spawn() -> None:
    world = WorldState(world_seed=42)
    controller = PlayerController(player_id="p1")
    player = controller.ensure_player(world, spawn=(3, 4))

    assert world.world_seed == 42
    assert player.position == (3, 4)
    assert "p1" in world.entities


def test_tick_progression_is_deterministic() -> None:
    world = WorldState(world_seed=777)
    controller = PlayerController(player_id="p1")
    controller.ensure_player(world, spawn=(0, 0))

    npc_system = NPCSystem()
    npc_system.add_npc(world, "npc-1", (0, 0))
    npc_system.set_schedule("npc-1", {1: Goal(kind="wander", target_position=(3, 0))})

    sim = Simulation(world)
    sim.register_system(npc_system.update)

    sim.run_steps(3)

    assert world.tick == 3
    assert world.time_of_day.tick_of_day == 3
    assert world.entities["npc-1"].position == (3, 0)


def test_save_load_round_trip(tmp_path: Path) -> None:
    world = WorldState(world_seed=99)
    controller = PlayerController(player_id="p1")
    controller.ensure_player(world, spawn=(1, 1))
    controller.gather_resource(world, "wood", amount=2)

    sim = Simulation(world)
    sim.run_steps(5)

    save_path = tmp_path / "snapshot.json"
    save_world(world, save_path)
    loaded = load_world(save_path)

    assert loaded.world_seed == world.world_seed
    assert loaded.tick == world.tick
    assert loaded.entities["p1"].inventory == world.entities["p1"].inventory
    assert loaded.time_of_day.tick_of_day == world.time_of_day.tick_of_day
