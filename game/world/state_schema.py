from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


CURRENT_SCHEMA_VERSION = 2


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class WorldState:
    """Canonical, deterministic world state persisted by snapshots and diffs."""

    schema_version: int = CURRENT_SCHEMA_VERSION
    world_version: int = 0
    seed: int = 0
    tick: int = 0
    entities: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        self.updated_at = _utc_now_iso()
        return {
            "schema_version": self.schema_version,
            "world_version": self.world_version,
            "seed": self.seed,
            "tick": self.tick,
            "entities": self.entities,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "WorldState":
        return cls(
            schema_version=payload["schema_version"],
            world_version=payload["world_version"],
            seed=payload["seed"],
            tick=payload["tick"],
            entities=payload.get("entities", {}),
            metadata=payload.get("metadata", {}),
            created_at=payload.get("created_at", _utc_now_iso()),
            updated_at=payload.get("updated_at", _utc_now_iso()),
        )


@dataclass(slots=True)
class WorldDiff:
    """Incremental world updates between two versions."""

    schema_version: int
    base_world_version: int
    target_world_version: int
    tick: int
    operations: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "base_world_version": self.base_world_version,
            "target_world_version": self.target_world_version,
            "tick": self.tick,
            "operations": self.operations,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "WorldDiff":
        return cls(
            schema_version=payload["schema_version"],
            base_world_version=payload["base_world_version"],
            target_world_version=payload["target_world_version"],
            tick=payload["tick"],
            operations=payload.get("operations", []),
            created_at=payload.get("created_at", _utc_now_iso()),
        )
