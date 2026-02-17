"""Entity registration and lookup for world chunks."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple


class EntityType(str, Enum):
    NPC = "npc"
    FAUNA = "fauna"
    RESOURCE = "resource"


@dataclass
class EntityRecord:
    entity_id: str
    entity_type: EntityType
    chunk_x: int
    chunk_y: int
    metadata: Dict[str, str] = field(default_factory=dict)


class EntityRegistry:
    """Tracks NPCs, fauna, and resources by chunk."""

    def __init__(self) -> None:
        self._by_id: Dict[str, EntityRecord] = {}
        self._by_chunk: Dict[Tuple[int, int], List[str]] = {}

    def upsert(self, record: EntityRecord) -> None:
        if record.entity_id in self._by_id:
            self.remove(record.entity_id)

        self._by_id[record.entity_id] = record
        self._by_chunk.setdefault((record.chunk_x, record.chunk_y), []).append(record.entity_id)

    def remove(self, entity_id: str) -> None:
        existing = self._by_id.pop(entity_id, None)
        if not existing:
            return

        key = (existing.chunk_x, existing.chunk_y)
        ids = self._by_chunk.get(key, [])
        if entity_id in ids:
            ids.remove(entity_id)
        if not ids and key in self._by_chunk:
            del self._by_chunk[key]

    def entities_in_chunk(self, chunk_x: int, chunk_y: int) -> List[EntityRecord]:
        ids = self._by_chunk.get((chunk_x, chunk_y), [])
        return [self._by_id[entity_id] for entity_id in ids]

    def list_by_type(self, entity_type: EntityType) -> List[EntityRecord]:
        return [record for record in self._by_id.values() if record.entity_type == entity_type]
