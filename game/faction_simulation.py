"""Faction-level world simulation for diplomacy, trade, and conflict."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Dict, List, Optional, Tuple

from engine.procgen.terrain import GenerationKey


RelationScore = int  # [-100, 100]


@dataclass
class Faction:
    id: str
    name: str
    military: float
    economy: float
    stability: float
    influence: float


@dataclass
class Treaty:
    a: str
    b: str
    kind: str  # non_aggression | trade | alliance
    remaining_turns: int


@dataclass
class FactionWorldState:
    factions: Dict[str, Faction]
    relations: Dict[Tuple[str, str], RelationScore] = field(default_factory=dict)
    treaties: List[Treaty] = field(default_factory=list)
    turn: int = 0


class FactionSimulation:
    def __init__(self, key: GenerationKey) -> None:
        self._key = key

    def tick(self, state: FactionWorldState) -> FactionWorldState:
        rng = random.Random(self._key.namespaced_seed(f"factions:{state.turn}"))
        state.turn += 1

        self._decay_treaties(state)

        faction_ids = sorted(state.factions)
        for i, a in enumerate(faction_ids):
            for b in faction_ids[i + 1 :]:
                rel_key = self._pair(a, b)
                current = state.relations.get(rel_key, 0)

                pressure = self._relation_pressure(state.factions[a], state.factions[b], rng)
                drift = rng.randint(-4, 4)
                new_rel = max(-100, min(100, current + pressure + drift))
                state.relations[rel_key] = new_rel

                if new_rel >= 40 and rng.random() < 0.1:
                    self._upsert_treaty(state, a, b, "trade", rng.randint(3, 7))
                if new_rel <= -55 and rng.random() < 0.12:
                    self._upsert_treaty(state, a, b, "non_aggression", rng.randint(2, 4))

                if new_rel <= -70:
                    self._simulate_conflict(state.factions[a], state.factions[b], rng)
                elif new_rel >= 55:
                    self._simulate_trade(state.factions[a], state.factions[b], rng)

        return state

    def _relation_pressure(self, a: Faction, b: Faction, rng: random.Random) -> int:
        econ_gap = abs(a.economy - b.economy)
        military_gap = abs(a.military - b.military)
        ideological_friction = rng.randint(-5, 5)
        return int(-(military_gap * 4) + (econ_gap * 2) + ideological_friction)

    def _simulate_conflict(self, a: Faction, b: Faction, rng: random.Random) -> None:
        a_power = a.military * (0.5 + a.stability)
        b_power = b.military * (0.5 + b.stability)
        total = max(0.001, a_power + b_power)
        a_loss = (b_power / total) * rng.uniform(0.03, 0.08)
        b_loss = (a_power / total) * rng.uniform(0.03, 0.08)
        a.military = max(0.0, a.military - a_loss)
        b.military = max(0.0, b.military - b_loss)
        a.stability = max(0.0, a.stability - rng.uniform(0.01, 0.03))
        b.stability = max(0.0, b.stability - rng.uniform(0.01, 0.03))

    def _simulate_trade(self, a: Faction, b: Faction, rng: random.Random) -> None:
        gain = rng.uniform(0.01, 0.04)
        a.economy = min(2.0, a.economy + gain)
        b.economy = min(2.0, b.economy + gain)
        a.influence = min(2.0, a.influence + gain * 0.5)
        b.influence = min(2.0, b.influence + gain * 0.5)

    def _upsert_treaty(
        self, state: FactionWorldState, a: str, b: str, kind: str, turns: int
    ) -> None:
        for treaty in state.treaties:
            if {treaty.a, treaty.b} == {a, b} and treaty.kind == kind:
                treaty.remaining_turns = max(treaty.remaining_turns, turns)
                return
        state.treaties.append(Treaty(a=a, b=b, kind=kind, remaining_turns=turns))

    def _decay_treaties(self, state: FactionWorldState) -> None:
        for treaty in state.treaties:
            treaty.remaining_turns -= 1
        state.treaties = [t for t in state.treaties if t.remaining_turns > 0]

    @staticmethod
    def _pair(a: str, b: str) -> Tuple[str, str]:
        return (a, b) if a < b else (b, a)


def relation_between(state: FactionWorldState, a: str, b: str) -> Optional[RelationScore]:
    return state.relations.get((a, b) if a < b else (b, a))
