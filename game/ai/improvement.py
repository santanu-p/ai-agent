from __future__ import annotations

from typing import Any, Dict

from game.engine.interfaces import ISelfImprovementPipeline


class NoOpSelfImprovementPipeline(ISelfImprovementPipeline):
    """Placeholder pipeline for future adaptive behavior tuning."""

    def run_cycle(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        moves = telemetry.get("moves", 0)
        return {
            "status": "ok",
            "note": f"Telemetry received. Moves this run: {moves}",
        }
