"""Game AI continuous improvement components."""

from .deployer import PatchDeployer
from .loop import AutonomousGameAILoop
from .metrics import KPICalculator, KPIThresholds
from .types import DeploymentRecord, KPIReport, Observation, PatchProposal, ValidationResult
from .validator import PatchValidator

__all__ = [
    "AutonomousGameAILoop",
    "PatchDeployer",
    "PatchValidator",
    "KPICalculator",
    "KPIThresholds",
    "Observation",
    "KPIReport",
    "PatchProposal",
    "ValidationResult",
    "DeploymentRecord",
]
