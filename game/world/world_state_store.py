"""Persistent per-chunk patch history and materialization."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from hashlib import blake2b
from pathlib import Path
from typing import Any, Dict, List, Optional


ChunkKey = str


@dataclass
class ChunkPatch:
    """Serializable patch operation for chunk-local state."""

    patch_id: str
    base_version: int
    operations: Dict[str, Any]
    author: str = "system"


class WorldStateStore:
    """Stores per-chunk state as deterministic patch chains.

    Reproducibility strategy:
    - Base world content is generated from the deterministic TerrainGenerator seed flow.
    - Runtime/world edits are recorded as ordered patch events per chunk.
    - Rehydration = deterministic base generation + replay of patch history.
    - Patch IDs and cumulative checksums allow clients/saves to verify parity.
    """

    def __init__(self, storage_dir: Path | str) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def chunk_key(chunk_x: int, chunk_y: int) -> ChunkKey:
        return f"{chunk_x},{chunk_y}"

    def append_patch(self, chunk_x: int, chunk_y: int, patch: ChunkPatch) -> int:
        payload = self._read_chunk_payload(chunk_x, chunk_y)
        history: List[Dict[str, Any]] = payload["patch_history"]

        current_version = len(history)
        if patch.base_version != current_version:
            raise ValueError(
                f"Patch base_version {patch.base_version} does not match current {current_version}"
            )

        history.append(asdict(patch))
        payload["checksum"] = self._history_checksum(history)
        self._write_chunk_payload(chunk_x, chunk_y, payload)
        return len(history)

    def get_patch_history(self, chunk_x: int, chunk_y: int) -> List[ChunkPatch]:
        payload = self._read_chunk_payload(chunk_x, chunk_y)
        return [ChunkPatch(**entry) for entry in payload["patch_history"]]

    def materialize_chunk_state(
        self, chunk_x: int, chunk_y: int, base_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        state = dict(base_state or {})
        for patch in self.get_patch_history(chunk_x, chunk_y):
            for key, value in patch.operations.items():
                state[key] = value
        return state

    def verify_chunk_checksum(self, chunk_x: int, chunk_y: int) -> bool:
        payload = self._read_chunk_payload(chunk_x, chunk_y)
        expected = self._history_checksum(payload["patch_history"])
        return expected == payload.get("checksum", "")

    def _chunk_path(self, chunk_x: int, chunk_y: int) -> Path:
        return self.storage_dir / f"chunk_{chunk_x}_{chunk_y}.json"

    def _read_chunk_payload(self, chunk_x: int, chunk_y: int) -> Dict[str, Any]:
        path = self._chunk_path(chunk_x, chunk_y)
        if not path.exists():
            return {"chunk": self.chunk_key(chunk_x, chunk_y), "patch_history": [], "checksum": ""}
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_chunk_payload(self, chunk_x: int, chunk_y: int, payload: Dict[str, Any]) -> None:
        path = self._chunk_path(chunk_x, chunk_y)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _history_checksum(history: List[Dict[str, Any]]) -> str:
        canonical = json.dumps(history, sort_keys=True, separators=(",", ":"))
        return blake2b(canonical.encode("utf-8"), digest_size=16).hexdigest()
