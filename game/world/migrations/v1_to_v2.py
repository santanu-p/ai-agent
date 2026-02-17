from __future__ import annotations

from typing import Any, Dict

from game.world.migrations import register


@register(1)
def migrate_v1_to_v2(payload: Dict[str, Any]) -> Dict[str, Any]:
    upgraded = dict(payload)
    # v2 introduces metadata and keeps deterministic defaults.
    upgraded.setdefault("metadata", {})
    upgraded["schema_version"] = 2
    return upgraded
