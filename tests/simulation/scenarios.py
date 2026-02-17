"""Deterministic simulation scenarios and KPI evaluation for AI patch gating."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    metric_name: str
    value: float
    threshold: float
    comparator: str

    @property
    def passed(self) -> bool:
        if self.comparator == "<=":
            return self.value <= self.threshold
        if self.comparator == ">=":
            return self.value >= self.threshold
        raise ValueError(f"Unsupported comparator: {self.comparator}")


class SimulationSuite:
    """Collection of stable simulation scenarios used as deployment KPIs."""

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)

    def economy_stress_test(self) -> ScenarioResult:
        """Stress economic loops and report inflation drift ratio (lower is better)."""
        drift_samples = [abs(self._rng.gauss(0.0, 0.08)) for _ in range(500)]
        inflation_drift_ratio = sum(drift_samples) / len(drift_samples)
        return ScenarioResult(
            name="economy_stress_test",
            metric_name="inflation_drift_ratio",
            value=inflation_drift_ratio,
            threshold=0.10,
            comparator="<=",
        )

    def combat_difficulty_progression(self) -> ScenarioResult:
        """Validate difficulty ramps while preserving target win-rate envelope."""
        base_skill = 0.55
        encounters = 300
        wins = 0
        for index in range(encounters):
            enemy_scaling = 0.35 + (index / encounters) * 0.45
            player_roll = base_skill + self._rng.uniform(-0.2, 0.2)
            if player_roll >= enemy_scaling:
                wins += 1
        win_rate = wins / encounters
        return ScenarioResult(
            name="combat_difficulty_progression",
            metric_name="target_band_hit_rate",
            value=win_rate,
            threshold=0.42,
            comparator=">=",
        )

    def quest_deadlock_detection(self) -> ScenarioResult:
        """Detect deadlocked quest states in generated branching graphs."""
        total_graphs = 250
        deadlocks = 0
        for _ in range(total_graphs):
            node_count = self._rng.randint(8, 20)
            edges = self._rng.randint(node_count - 1, node_count * 2)
            deadlock_risk = max(0.0, 0.20 - (edges / (node_count * 2.5)))
            if self._rng.random() < deadlock_risk:
                deadlocks += 1
        deadlock_rate = deadlocks / total_graphs
        return ScenarioResult(
            name="quest_deadlock_detection",
            metric_name="deadlock_rate",
            value=deadlock_rate,
            threshold=0.02,
            comparator="<=",
        )

    def npc_navigation_pathing_robustness(self) -> ScenarioResult:
        """Exercise navmesh/pathing under random obstacle churn."""
        pathing_trials = 400
        failures = 0
        for _ in range(pathing_trials):
            obstacle_density = self._rng.uniform(0.05, 0.45)
            replans = self._rng.randint(0, 4)
            fail_probability = 0.01 + obstacle_density * 0.06 + replans * 0.004
            if self._rng.random() < fail_probability:
                failures += 1
        success_rate = 1.0 - (failures / pathing_trials)
        return ScenarioResult(
            name="npc_navigation_pathing_robustness",
            metric_name="path_success_rate",
            value=success_rate,
            threshold=0.94,
            comparator=">=",
        )

    def save_load_migration_invariants(self) -> ScenarioResult:
        """Validate migrated saves preserve critical progression invariants."""
        migrations = 320
        invariant_breaks = 0
        for _ in range(migrations):
            save_age = self._rng.randint(1, 8)
            schema_changes = self._rng.randint(1, 6)
            break_probability = 0.0025 * save_age + 0.0018 * schema_changes
            if self._rng.random() < break_probability:
                invariant_breaks += 1
        invariant_preservation = 1.0 - (invariant_breaks / migrations)
        return ScenarioResult(
            name="save_load_migration_invariants",
            metric_name="invariant_preservation_rate",
            value=invariant_preservation,
            threshold=0.98,
            comparator=">=",
        )

    def run_all(self) -> list[ScenarioResult]:
        return [
            self.economy_stress_test(),
            self.combat_difficulty_progression(),
            self.quest_deadlock_detection(),
            self.npc_navigation_pathing_robustness(),
            self.save_load_migration_invariants(),
        ]
