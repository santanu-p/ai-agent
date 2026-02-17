from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

ChunkCoord = tuple[int, int]


@dataclass(frozen=True)
class ChunkPatch:
    """Immutable patch event for chunk-local world state.

    Patches form a hash chain so all clients can validate ordering and history:
      patch_hash = H(chunk_key + parent_hash + canonical_json(ops) + metadata)
    """

    chunk: ChunkCoord
    operations: list[dict[str, Any]]
    author_system: str
    patch_id: str
    parent_patch_id: str | None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk": list(self.chunk),
            "operations": self.operations,
            "author_system": self.author_system,
            "patch_id": self.patch_id,
            "parent_patch_id": self.parent_patch_id,
            "created_at": self.created_at,
            "tags": list(self.tags),
        }


class WorldStateStore:
    """Persistent diff store for per-chunk patch history.

    Strategy:
      1. Deterministic terrain is generated from world_seed + chunk coordinates.
      2. Runtime mutations are written as append-only patches per chunk.
      3. Reproduction is base_generation(chunk, world_seed) + ordered_patch_chain(chunk).

    The on-disk format is JSONL so history is inspectable and merge-friendly.
    """

    def __init__(self, storage_dir: str | Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _chunk_key(self, chunk: ChunkCoord) -> str:
        return f"{chunk[0]}_{chunk[1]}"

    def _chunk_path(self, chunk: ChunkCoord) -> Path:
        return self.storage_dir / f"chunk_{self._chunk_key(chunk)}.jsonl"

    def _canonical_ops_hash(
        self,
        chunk: ChunkCoord,
        operations: list[dict[str, Any]],
        parent_patch_id: str | None,
        author_system: str,
        created_at: str,
        tags: tuple[str, ...],
    ) -> str:
        payload = {
            "chunk": list(chunk),
            "operations": operations,
            "parent_patch_id": parent_patch_id,
            "author_system": author_system,
            "created_at": created_at,
            "tags": list(tags),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def get_patch_chain(self, chunk: ChunkCoord) -> list[ChunkPatch]:
        path = self._chunk_path(chunk)
        if not path.exists():
            return []

        chain: list[ChunkPatch] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                raw = json.loads(line)
                chain.append(
                    ChunkPatch(
                        chunk=(raw["chunk"][0], raw["chunk"][1]),
                        operations=raw["operations"],
                        author_system=raw["author_system"],
                        patch_id=raw["patch_id"],
                        parent_patch_id=raw["parent_patch_id"],
                        created_at=raw["created_at"],
                        tags=tuple(raw.get("tags", [])),
                    )
                )

        self._validate_chain(chunk, chain)
        return chain

    def append_patch(
        self,
        chunk: ChunkCoord,
        operations: list[dict[str, Any]],
        author_system: str,
        tags: tuple[str, ...] = (),
    ) -> ChunkPatch:
        chain = self.get_patch_chain(chunk)
        parent = chain[-1].patch_id if chain else None
        created_at = datetime.now(timezone.utc).isoformat()
        patch_id = self._canonical_ops_hash(
            chunk=chunk,
            operations=operations,
            parent_patch_id=parent,
            author_system=author_system,
            created_at=created_at,
            tags=tags,
        )

        patch = ChunkPatch(
            chunk=chunk,
            operations=operations,
            author_system=author_system,
            patch_id=patch_id,
            parent_patch_id=parent,
            created_at=created_at,
            tags=tags,
        )

        path = self._chunk_path(chunk)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(patch.to_dict(), sort_keys=True) + "\n")

        return patch

    def materialize_chunk_state(self, chunk: ChunkCoord) -> dict[str, Any]:
        """Returns an operation-indexed state view for replay/inspection."""
        chain = self.get_patch_chain(chunk)
        state: dict[str, Any] = {"ops": []}
        for patch in chain:
            state["ops"].extend(patch.operations)
        return state

    def _validate_chain(self, chunk: ChunkCoord, chain: list[ChunkPatch]) -> None:
        expected_parent = None
        for patch in chain:
            if patch.parent_patch_id != expected_parent:
                raise ValueError(
                    f"Patch chain broken for chunk={chunk}: expected parent={expected_parent}, "
                    f"found={patch.parent_patch_id}"
                )
            expected_parent = patch.patch_id
