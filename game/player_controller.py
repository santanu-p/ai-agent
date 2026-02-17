from __future__ import annotations

from dataclasses import dataclass, field

from engine.world_state import Entity, WorldState


@dataclass
class PlayerController:
    player_id: str
    world: WorldState
    inventory: dict[str, int] = field(default_factory=dict)

    @classmethod
    def spawn(cls, world: WorldState, player_id: str = "player", x: int = 0, y: int = 0) -> "PlayerController":
        world.add_entity(Entity(entity_id=player_id, name="Player", x=x, y=y))
        return cls(player_id=player_id, world=world)

    @property
    def position(self) -> tuple[int, int]:
        player = self.world.entities[self.player_id]
        return player.x, player.y

    def move(self, dx: int, dy: int) -> tuple[int, int]:
        player = self.world.entities[self.player_id]
        player.x += dx
        player.y += dy
        self.world.get_chunk_at(player.x, player.y)
        return player.x, player.y

    def interact(self, resource_name: str, amount: int = 1) -> int:
        player = self.world.entities[self.player_id]
        chunk = self.world.get_chunk_at(player.x, player.y)
        available = chunk.resources.get(resource_name, 0)
        harvested = min(amount, available)
        chunk.resources[resource_name] = available - harvested
        if harvested:
            self.inventory[resource_name] = self.inventory.get(resource_name, 0) + harvested
        return harvested
