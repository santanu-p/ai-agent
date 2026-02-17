"""Red-team test catalog for AI-driven changes.

The scenarios in this module are used to proactively evaluate exploitability,
griefing potential, and economy abuse before releasing AI-authored updates.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List


class RedTeamCategory(str, Enum):
    EXPLOIT_GENERATION = "exploit_generation"
    GRIEFING_SCENARIO = "griefing_scenario"
    ECONOMY_ABUSE = "economy_abuse"


@dataclass(frozen=True)
class RedTeamScenario:
    id: str
    category: RedTeamCategory
    description: str
    expected_failure_signal: str


RED_TEAM_SCENARIOS: tuple[RedTeamScenario, ...] = (
    RedTeamScenario(
        id="rt.exploit.sequence-break",
        category=RedTeamCategory.EXPLOIT_GENERATION,
        description=(
            "Attempt sequence-breaking progression by chaining timing-sensitive "
            "actions across zones and reconnect boundaries."
        ),
        expected_failure_signal="Unbounded progression gain or skipped progression gates.",
    ),
    RedTeamScenario(
        id="rt.exploit.duplication",
        category=RedTeamCategory.EXPLOIT_GENERATION,
        description="Probe item/currency duplication via rollback and retry races.",
        expected_failure_signal="Inventory or currency increases without valid sinks.",
    ),
    RedTeamScenario(
        id="rt.grief.spawn-camping",
        category=RedTeamCategory.GRIEFING_SCENARIO,
        description=(
            "Simulate coordinated spawn-camping and targeting asymmetry against "
            "new or under-geared players."
        ),
        expected_failure_signal="Severe win-rate suppression for protected cohorts.",
    ),
    RedTeamScenario(
        id="rt.grief.matchmaking-manipulation",
        category=RedTeamCategory.GRIEFING_SCENARIO,
        description="Attempt MMR manipulation through intentional loss trading.",
        expected_failure_signal="Match quality degradation and asymmetric stomps.",
    ),
    RedTeamScenario(
        id="rt.econ.inflation-loop",
        category=RedTeamCategory.ECONOMY_ABUSE,
        description="Stress-test repeatable loops that mint net-positive currency.",
        expected_failure_signal="Sustained economy inflation outside forecast range.",
    ),
    RedTeamScenario(
        id="rt.econ.auction-cornering",
        category=RedTeamCategory.ECONOMY_ABUSE,
        description="Model market-cornering and price manipulation by colluding actors.",
        expected_failure_signal="Price spikes and item accessibility collapse.",
    ),
)


def scenarios_for(category: RedTeamCategory) -> List[RedTeamScenario]:
    """Return all scenarios for the provided red-team category."""

    return [scenario for scenario in RED_TEAM_SCENARIOS if scenario.category == category]


def scenario_ids(scenarios: Iterable[RedTeamScenario]) -> List[str]:
    """Extract stable scenario IDs for reporting and CI gates."""

    return [scenario.id for scenario in scenarios]
