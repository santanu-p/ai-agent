from __future__ import annotations

from typing import Callable


ToolFn = Callable[[str], str]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {
            "social.publish": lambda payload: f"scheduled social publish: {payload}",
            "dev.pipeline": lambda payload: f"dev pipeline started: {payload}",
            "games.simulate": lambda payload: f"game simulation launched: {payload}",
            "ops.observe": lambda payload: f"telemetry captured: {payload}",
        }

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def execute(self, name: str, payload: str) -> str:
        fn = self._tools.get(name)
        if not fn:
            raise KeyError(f"tool not found: {name}")
        return fn(payload)

