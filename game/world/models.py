from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class Position:
    x: int = 0
    y: int = 0

    def move(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy


@dataclass
class Player:
    name: str
    position: Position

    def to_dict(self) -> dict:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        pos = Position(**data["position"])
        return cls(name=data["name"], position=pos)


@dataclass
class World:
    name: str
    seed: int
    width: int = 20
    height: int = 20

    def clamp(self, pos: Position) -> None:
        pos.x = max(0, min(self.width - 1, pos.x))
        pos.y = max(0, min(self.height - 1, pos.y))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "World":
        return cls(**data)
