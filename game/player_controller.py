"""Player control actions for movement and interaction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from engine.world_state import Entity, WorldState, world_to_chunk


@dataclass
class PlayerController:
    player_id: str

    def ensure_player(self, world: WorldState, spawn: Tuple[int, int]) -> Entity:
        player = world.entities.get(self.player_id)
        if player:
            return player

        player = Entity(entity_id=self.player_id, kind="player", position=spawn)
        world.add_entity(player)
        return player

    def move(self, world: WorldState, delta: Tuple[int, int]) -> None:
        player = world.entities[self.player_id]
        old_chunk = world_to_chunk(player.position)
        new_pos = player.position[0] + delta[0], player.position[1] + delta[1]
        new_chunk = world_to_chunk(new_pos)
        player.position = new_pos

        if old_chunk != new_chunk:
            old_chunk_data = world.get_or_create_chunk(old_chunk)
            if self.player_id in old_chunk_data.entity_ids:
                old_chunk_data.entity_ids.remove(self.player_id)
            new_chunk_data = world.get_or_create_chunk(new_chunk)
            if self.player_id not in new_chunk_data.entity_ids:
                new_chunk_data.entity_ids.append(self.player_id)

    def gather_resource(self, world: WorldState, resource_type: str, amount: int = 1) -> int:
        player = world.entities[self.player_id]
        chunk = world.get_or_create_chunk(world_to_chunk(player.position))
        available = chunk.resources.get(resource_type, 0)
        gathered = min(amount, available)
        chunk.resources[resource_type] = available - gathered
        player.inventory[resource_type] = player.inventory.get(resource_type, 0) + gathered
        return gathered

    def interact(self, world: WorldState, target_id: str) -> str:
        if target_id not in world.entities:
            return "missing_target"
        return f"interacted:{target_id}"
