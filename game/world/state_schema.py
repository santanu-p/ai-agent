"""World-state schemas with explicit version fields."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping

SCHEMA_VERSION = 2


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class EntityState:
    """Canonical state for one world entity."""

    entity_id: str
    kind: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class WorldState:
    """Canonical deterministic world-state payload."""

    world_id: str
    tick: int
    entities: List[EntityState] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class SnapshotEnvelope:
    """Serialized snapshot wrapper with integrity metadata."""

    snapshot_id: str
    created_at: str
    state: Dict[str, Any]
    state_hash: str
    signature: str
    version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class DiffEnvelope:
    """Serialized incremental diff wrapper with integrity metadata."""

    diff_id: str
    snapshot_id: str
    tick: int
    created_at: str
    changes: Dict[str, Any]
    diff_hash: str
    signature: str
    version: int = SCHEMA_VERSION


def normalize_world_state(state: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalize world state into deterministic order and include explicit version."""
    entities = sorted(state.get("entities", []), key=lambda x: x["entity_id"])
    canonical_entities: List[Dict[str, Any]] = []
    for entity in entities:
        canonical_entities.append(
            {
                "entity_id": entity["entity_id"],
                "kind": entity["kind"],
                "attributes": dict(sorted(entity.get("attributes", {}).items())),
                "version": int(entity.get("version", SCHEMA_VERSION)),
            }
        )

    metadata = dict(sorted(state.get("metadata", {}).items()))

    return {
        "world_id": state["world_id"],
        "tick": int(state["tick"]),
        "entities": canonical_entities,
        "metadata": metadata,
        "version": int(state.get("version", SCHEMA_VERSION)),
    }
