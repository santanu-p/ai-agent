from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class IWorldGenerator(ABC):
    """Creates or loads world state."""

    @abstractmethod
    def generate(self, seed: int | None = None) -> Dict[str, Any]:
        raise NotImplementedError


class IAgentController(ABC):
    """Decides player or agent actions for each frame/tick."""

    @abstractmethod
    def next_action(self, world_state: Dict[str, Any]) -> str:
        raise NotImplementedError


class ISelfImprovementPipeline(ABC):
    """Consumes run history and suggests upgrades or tunings."""

    @abstractmethod
    def run_cycle(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
