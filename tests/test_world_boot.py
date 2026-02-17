from __future__ import annotations

from pathlib import Path

from engine.persistence import load_snapshot, save_snapshot
from engine.simulation import Simulation
from engine.world_state import WorldState
from game.npc_system import NPCSystem
from game.player_controller import PlayerController


def test_world_initialization_smoke() -> None:
    world = WorldState.bootstrap(seed=123, chunk_radius=1)

    assert world.seed == 123
    assert len(world.chunks) == 9
    assert world.weather.condition in {"clear", "cloudy", "windy", "rain"}


def test_tick_progression_and_deterministic_order() -> None:
    world = WorldState.bootstrap(seed=99)
    sim = Simulation(world=world)
    order: list[str] = []

    def first_system(current_world: WorldState, _: int) -> None:
        order.append(f"first:{current_world.time_of_day.tick}")

    def second_system(current_world: WorldState, _: int) -> None:
        order.append(f"second:{current_world.time_of_day.tick}")

    sim.register_system("first", first_system)
    sim.register_system("second", second_system)

    sim.run_steps(steps=3)

    assert sim.system_order == ["first", "second"]
    assert order == [
        "first:0",
        "second:0",
        "first:1",
        "second:1",
        "first:2",
        "second:2",
    ]
    assert world.time_of_day.tick == 3


def test_save_load_integrity(tmp_path: Path) -> None:
    world = WorldState.bootstrap(seed=7)
    player = PlayerController.spawn(world, x=4, y=4)
    player.interact("wood", amount=2)

    npc_system = NPCSystem(world)
    npc_system.add_npc("npc_1", "Gatherer", x=5, y=5, goal=(7, 5), schedule_hour=6)

    sim = Simulation(world=world)
    sim.register_system("npc_system", npc_system.update)
    sim.run_steps(2)

    snapshot = tmp_path / "snapshot.json"
    save_snapshot(world, snapshot)
    reloaded = load_snapshot(snapshot)

    assert reloaded.seed == world.seed
    assert reloaded.time_of_day.tick == world.time_of_day.tick
    assert reloaded.entities["player"].x == world.entities["player"].x
    assert reloaded.entities["npc_1"].y == world.entities["npc_1"].y
    assert reloaded.chunks[(0, 0)].resources["wood"] == world.chunks[(0, 0)].resources["wood"]
