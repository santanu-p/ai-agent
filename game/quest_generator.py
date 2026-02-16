"""Dynamic quest generation from world state and faction simulation."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Dict, List, Sequence

from engine.procgen.poi_generator import POI, POIType
from engine.procgen.terrain import GenerationKey
from game.faction_simulation import FactionWorldState, relation_between


@dataclass(frozen=True)
class Quest:
    id: str
    title: str
    description: str
    category: str
    recommended_level: int
    rewards: Dict[str, int]


class QuestGenerator:
    def __init__(self, key: GenerationKey) -> None:
        self._key = key

    def generate(
        self,
        region_id: str,
        turn: int,
        world_pois: Sequence[POI],
        faction_state: FactionWorldState,
        max_quests: int = 5,
    ) -> List[Quest]:
        rng = random.Random(self._key.namespaced_seed(f"quests:{region_id}:{turn}"))
        quests: List[Quest] = []

        settlements = [poi for poi in world_pois if poi.type == POIType.SETTLEMENT]
        dungeons = [poi for poi in world_pois if poi.type == POIType.DUNGEON]
        ruins = [poi for poi in world_pois if poi.type == POIType.RUIN]

        quests.extend(self._faction_diplomacy_hooks(faction_state, rng))
        quests.extend(self._trade_and_logistics_hooks(settlements, faction_state, rng))
        quests.extend(self._exploration_hooks(dungeons, ruins, rng))

        rng.shuffle(quests)
        return quests[:max_quests]

    def _faction_diplomacy_hooks(
        self, faction_state: FactionWorldState, rng: random.Random
    ) -> List[Quest]:
        ids = sorted(faction_state.factions)
        quests: List[Quest] = []
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                rel = relation_between(faction_state, a, b)
                if rel is None:
                    continue
                if rel <= -60:
                    quests.append(
                        self._quest(
                            rng,
                            category="war",
                            title=f"Skirmish on the {a}-{b} Frontier",
                            description=(
                                f"Hostility between {a} and {b} has escalated. "
                                "Raid supply lines or broker a ceasefire."
                            ),
                            level=12,
                            gold=240,
                            reputation=30,
                        )
                    )
                elif rel >= 55:
                    quests.append(
                        self._quest(
                            rng,
                            category="diplomacy",
                            title=f"Seal the {a}-{b} Pact",
                            description=(
                                f"{a} and {b} are aligned. Escort envoys and secure "
                                "terms before rivals sabotage the treaty."
                            ),
                            level=8,
                            gold=160,
                            reputation=45,
                        )
                    )
        return quests

    def _trade_and_logistics_hooks(
        self,
        settlements: Sequence[POI],
        faction_state: FactionWorldState,
        rng: random.Random,
    ) -> List[Quest]:
        if len(settlements) < 2:
            return []
        richest = sorted(
            faction_state.factions.values(), key=lambda f: f.economy, reverse=True
        )[:2]
        if len(richest) < 2:
            return []

        a, b = richest
        origin, destination = rng.sample(list(settlements), 2)
        return [
            self._quest(
                rng,
                category="trade",
                title=f"Caravan Between {origin.metadata.get('size', 'towns').title()}",
                description=(
                    f"Deliver a high-value caravan from ({origin.x}, {origin.y}) to "
                    f"({destination.x}, {destination.y}) while {a.name} and {b.name} "
                    "compete for regional dominance."
                ),
                level=6,
                gold=120,
                reputation=20,
            )
        ]

    def _exploration_hooks(
        self,
        dungeons: Sequence[POI],
        ruins: Sequence[POI],
        rng: random.Random,
    ) -> List[Quest]:
        quests: List[Quest] = []
        if dungeons:
            target = rng.choice(list(dungeons))
            quests.append(
                self._quest(
                    rng,
                    category="dungeon",
                    title="Threat Below the Peaks",
                    description=(
                        f"Scouts report danger in dungeon at ({target.x}, {target.y}). "
                        "Clear the lair and recover strategic maps."
                    ),
                    level=10,
                    gold=210,
                    reputation=25,
                )
            )
        if ruins:
            target = rng.choice(list(ruins))
            quests.append(
                self._quest(
                    rng,
                    category="exploration",
                    title="Echoes of a Fallen Age",
                    description=(
                        f"Investigate ruins at ({target.x}, {target.y}) and return with "
                        "artifacts to influence current power struggles."
                    ),
                    level=7,
                    gold=140,
                    reputation=18,
                )
            )
        return quests

    def _quest(
        self,
        rng: random.Random,
        category: str,
        title: str,
        description: str,
        level: int,
        gold: int,
        reputation: int,
    ) -> Quest:
        quest_id = f"q-{rng.randrange(10**9):09d}"
        return Quest(
            id=quest_id,
            title=title,
            description=description,
            category=category,
            recommended_level=level,
            rewards={"gold": gold, "reputation": reputation},
        )
