"""Red-team scenario generation and checks for AI-driven changes.

This module provides lightweight, code-centric checks for exploit generation,
griefing amplification, and economy abuse detection.
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Scenario:
    name: str
    category: str
    severity: str
    description: str


def generate_exploit_scenarios() -> List[Scenario]:
    return [
        Scenario(
            name="dupe-item-chain",
            category="exploit_generation",
            severity="critical",
            description="Sequence actions to duplicate high-value items via rollback race.",
        ),
        Scenario(
            name="cooldown-bypass-loop",
            category="exploit_generation",
            severity="high",
            description="Explore state desyncs that reset ability cooldowns.",
        ),
    ]


def generate_griefing_scenarios() -> List[Scenario]:
    return [
        Scenario(
            name="matchmaking-smurf-funnel",
            category="griefing",
            severity="high",
            description="Detect whether ranking updates enable intentional novice farming.",
        ),
        Scenario(
            name="resource-denial-kiting",
            category="griefing",
            severity="medium",
            description="Check if AI tuning enables indefinite resource denial loops.",
        ),
    ]


def generate_economy_abuse_scenarios() -> List[Scenario]:
    return [
        Scenario(
            name="auction-price-corner",
            category="economy_abuse",
            severity="critical",
            description="Probe if bots can corner commodity supply and force inflation spikes.",
        ),
        Scenario(
            name="reward-funnel-alt-ring",
            category="economy_abuse",
            severity="high",
            description="Assess cross-account reward funneling under new reward weights.",
        ),
    ]


def detect_high_risk_findings(results: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Return findings that should block deployment.

    Expected input item shape: {"name": str, "status": "pass|fail", "severity": str}
    """

    block_severities = {"critical", "high"}
    return [
        finding
        for finding in results
        if finding.get("status") == "fail" and finding.get("severity") in block_severities
    ]
