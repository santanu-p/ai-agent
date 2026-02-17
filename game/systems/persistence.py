from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class SaveLoadSystem:
    def __init__(self, save_path: str = "savegame.json") -> None:
        self.save_path = Path(save_path)

    def save(self, world_state: Dict[str, Any]) -> None:
        self.save_path.write_text(json.dumps(world_state, indent=2), encoding="utf-8")

    def load(self) -> Dict[str, Any]:
        if not self.save_path.exists():
            raise FileNotFoundError(f"No save file at {self.save_path}")
        return json.loads(self.save_path.read_text(encoding="utf-8"))
