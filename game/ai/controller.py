from __future__ import annotations

from typing import Any, Dict

from game.engine.interfaces import IAgentController


class KeyboardAgentController(IAgentController):
    """Maps keyboard text input to movement actions."""

    VALID_ACTIONS = {"w", "a", "s", "d", "save", "load", "quit"}

    def next_action(self, world_state: Dict[str, Any]) -> str:
        action = input("Action (w/a/s/d, save, load, quit): ").strip().lower()
        return action if action in self.VALID_ACTIONS else "noop"
