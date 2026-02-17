"""Dynamic quest generation from evolving world and faction state."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
import random
from typing import Dict, Iterable, List, Sequence

from game.faction_simulation import Faction


@dataclass(frozen=True)
class WorldSignal:
    key: str
    value: float
    description: str


@dataclass(frozen=True)
class WorldState:
    tick: int
    active_pois: Dict[str, int]
    danger_regions: Sequence[str]
    signals: Sequence[WorldSignal]


@dataclass(frozen=True)
class Quest:
    quest_id: str
    title: str
    objective: str
    sponsors: List[str]
    reward_hint: str


class QuestGenerator:
    """Produces reproducible non-static quests from live simulation signals."""

    def __init__(self, seed: int, version: str):
        self.seed = seed
        self.version = version

    def generate(self, world: WorldState, factions: Iterable[Faction], count: int = 5) -> List[Quest]:
        faction_list = list(factions)
        rng = self._rng(world.tick, len(faction_list), len(world.signals))

        candidates: List[Quest] = []
        candidates.extend(self._from_conflicts(world, faction_list, rng))
        candidates.extend(self._from_trade(world, faction_list, rng))
        candidates.extend(self._from_exploration(world, faction_list, rng))

        rng.shuffle(candidates)
        return candidates[:count]

    def _from_conflicts(self, world: WorldState, factions: Sequence[Faction], rng: random.Random) -> List[Quest]:
        quests: List[Quest] = []
        for faction in factions:
            hostile = [target for target, relation in faction.relations.items() if relation < -0.45]
            if not hostile:
                continue
            rival = rng.choice(hostile)
            quests.append(
                self._quest(
                    world.tick,
                    "conflict",
                    f"Sabotage {rival} supply lines",
                    f"{faction.name} seeks deniable agents to disrupt logistics before open war.",
                    [faction.faction_id],
                    "rare military equipment",
                )
            )
        return quests

    def _from_trade(self, world: WorldState, factions: Sequence[Faction], rng: random.Random) -> List[Quest]:
        quests: List[Quest] = []
        scarcity = next((signal for signal in world.signals if signal.key == "scarcity_index"), None)
        if scarcity and scarcity.value > 0.5:
            sponsor = rng.choice(factions).faction_id if factions else "guild"
            quests.append(
                self._quest(
                    world.tick,
                    "trade",
                    "Restore caravan throughput",
                    "Supply chains are collapsing; escort convoys through contested roads.",
                    [sponsor],
                    "market access discount",
                )
            )
        return quests

    def _from_exploration(self, world: WorldState, factions: Sequence[Faction], rng: random.Random) -> List[Quest]:
        quests: List[Quest] = []
        dungeon_count = world.active_pois.get("dungeon", 0)
        ruin_count = world.active_pois.get("ruin", 0)
        if dungeon_count + ruin_count == 0:
            return quests

        sponsor = rng.choice(factions).faction_id if factions else "cartographers"
        region = rng.choice(world.danger_regions) if world.danger_regions else "frontier"
        title = "Map the Sunken Vault" if dungeon_count > ruin_count else "Recover Relics of the Ancients"
        objective = f"Travel to the {region} and chart newly surfaced sites before rivals do."
        quests.append(self._quest(world.tick, "exploration", title, objective, [sponsor], "artifact claims"))
        return quests

    def _quest(self, tick: int, kind: str, title: str, objective: str, sponsors: List[str], reward_hint: str) -> Quest:
        quest_id = blake2b(
            f"quest:{self.seed}:{self.version}:{tick}:{kind}:{title}".encode(),
            digest_size=8,
        ).hexdigest()
        return Quest(quest_id=quest_id, title=title, objective=objective, sponsors=sponsors, reward_hint=reward_hint)

    def _rng(self, tick: int, faction_count: int, signal_count: int) -> random.Random:
        digest = blake2b(
            f"quest:{self.seed}:{self.version}:{tick}:{faction_count}:{signal_count}".encode(),
            digest_size=16,
        ).digest()
        return random.Random(int.from_bytes(digest, "big"))
