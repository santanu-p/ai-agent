"""Faction simulation for diplomacy, trade, and conflict evolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import blake2b
import random
from typing import Dict, List


@dataclass
class Faction:
    faction_id: str
    name: str
    resources: float
    military: float
    stability: float
    relations: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class FactionEvent:
    tick: int
    kind: str
    source: str
    target: str
    magnitude: float
    summary: str


class FactionSimulation:
    """Deterministic faction state progression seeded by world seed + version."""

    def __init__(self, seed: int, version: str):
        self.seed = seed
        self.version = version

    def step(self, factions: Dict[str, Faction], tick: int) -> List[FactionEvent]:
        events: List[FactionEvent] = []
        ids = sorted(factions)
        for source_id in ids:
            source = factions[source_id]
            for target_id in ids:
                if source_id == target_id:
                    continue

                target = factions[target_id]
                relation = source.relations.get(target_id, 0.0)
                rng = self._rng(tick, source_id, target_id)

                if relation > 0.35 and source.resources > 25 and target.resources > 20 and rng.random() < 0.28:
                    trade_value = 1 + (source.resources + target.resources) * 0.01
                    source.resources += trade_value * 0.4
                    target.resources += trade_value * 0.4
                    source.relations[target_id] = min(1.0, relation + 0.03)
                    events.append(
                        FactionEvent(
                            tick=tick,
                            kind="trade",
                            source=source_id,
                            target=target_id,
                            magnitude=trade_value,
                            summary=f"{source.name} and {target.name} exchanged caravan goods.",
                        )
                    )
                elif relation < -0.35 and source.military > 10 and rng.random() < 0.25:
                    pressure = source.military / max(target.military, 1)
                    conflict = min(5.0, pressure * (0.5 + rng.random()))
                    source.military = max(0.0, source.military - conflict * 0.25)
                    target.military = max(0.0, target.military - conflict * 0.45)
                    target.stability = max(0.0, target.stability - conflict * 0.08)
                    source.relations[target_id] = max(-1.0, relation - 0.04)
                    events.append(
                        FactionEvent(
                            tick=tick,
                            kind="conflict",
                            source=source_id,
                            target=target_id,
                            magnitude=conflict,
                            summary=f"{source.name} raided border holdings of {target.name}.",
                        )
                    )
                elif rng.random() < 0.15:
                    drift = (rng.random() - 0.5) * 0.06
                    source.relations[target_id] = max(-1.0, min(1.0, relation + drift))
                    if abs(drift) > 0.02:
                        events.append(
                            FactionEvent(
                                tick=tick,
                                kind="diplomacy",
                                source=source_id,
                                target=target_id,
                                magnitude=drift,
                                summary=f"{source.name} diplomatic standing shifted with {target.name}.",
                            )
                        )

            source.resources = max(0.0, source.resources + 0.5 - (1.0 - source.stability) * 0.8)
            source.stability = max(0.0, min(1.0, source.stability + 0.01 * (source.resources > 10) - 0.01 * (source.military < 5)))
        return events

    def _rng(self, tick: int, source_id: str, target_id: str) -> random.Random:
        digest = blake2b(
            f"faction:{self.seed}:{self.version}:{tick}:{source_id}:{target_id}".encode(),
            digest_size=16,
        ).digest()
        return random.Random(int.from_bytes(digest, "big"))
