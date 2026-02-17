"""Migration script from schema version 1 to 2."""

from __future__ import annotations

from typing import Any, Dict, Mapping


def migrate_v1_to_v2(state: Mapping[str, Any]) -> Dict[str, Any]:
    migrated = dict(state)
    migrated.setdefault("metadata", {})
    migrated_entities = []
    for entity in migrated.get("entities", []):
        e = dict(entity)
        e.setdefault("attributes", {})
        e["version"] = 2
        migrated_entities.append(e)
    migrated["entities"] = migrated_entities
    migrated["version"] = 2
    return migrated
