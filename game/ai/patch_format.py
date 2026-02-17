"""Restricted patch format for behavior/policy deltas only."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import json


_ALLOWED_SCOPES = {"behavior", "policy"}
_ALLOWED_OPS = {"set", "increment", "decrement", "append", "remove"}


@dataclass(frozen=True)
class DeltaOperation:
    scope: str
    target: str
    op: str
    value: Any

    def validate(self) -> None:
        if self.scope not in _ALLOWED_SCOPES:
            raise ValueError(f"invalid scope: {self.scope}")
        if self.op not in _ALLOWED_OPS:
            raise ValueError(f"invalid op: {self.op}")
        if self.target.startswith("code."):
            raise ValueError("code mutation targets are blocked")


@dataclass(frozen=True)
class AIPatch:
    patch_id: str
    parent_patch_id: str | None
    created_at: str
    rationale: str
    deltas: list[DeltaOperation] = field(default_factory=list)

    @classmethod
    def new(cls, patch_id: str, rationale: str, deltas: list[DeltaOperation], parent_patch_id: str | None = None) -> "AIPatch":
        return cls(
            patch_id=patch_id,
            parent_patch_id=parent_patch_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            rationale=rationale,
            deltas=deltas,
        )

    def validate(self) -> None:
        if not self.patch_id:
            raise ValueError("patch_id must be non-empty")
        if not self.deltas:
            raise ValueError("patch must contain at least one delta")
        for delta in self.deltas:
            delta.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "patch_id": self.patch_id,
            "parent_patch_id": self.parent_patch_id,
            "created_at": self.created_at,
            "rationale": self.rationale,
            "deltas": [
                {
                    "scope": d.scope,
                    "target": d.target,
                    "op": d.op,
                    "value": d.value,
                }
                for d in self.deltas
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AIPatch":
        deltas = [DeltaOperation(**raw) for raw in payload.get("deltas", [])]
        patch = cls(
            patch_id=payload["patch_id"],
            parent_patch_id=payload.get("parent_patch_id"),
            created_at=payload["created_at"],
            rationale=payload["rationale"],
            deltas=deltas,
        )
        patch.validate()
        return patch

    @classmethod
    def from_json(cls, body: str) -> "AIPatch":
        return cls.from_dict(json.loads(body))


PATCH_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["patch_id", "created_at", "rationale", "deltas"],
    "additionalProperties": False,
    "properties": {
        "patch_id": {"type": "string", "minLength": 1},
        "parent_patch_id": {"type": ["string", "null"]},
        "created_at": {"type": "string", "format": "date-time"},
        "rationale": {"type": "string", "minLength": 1},
        "deltas": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["scope", "target", "op", "value"],
                "additionalProperties": False,
                "properties": {
                    "scope": {"type": "string", "enum": sorted(_ALLOWED_SCOPES)},
                    "target": {"type": "string", "minLength": 1},
                    "op": {"type": "string", "enum": sorted(_ALLOWED_OPS)},
                    "value": {},
                },
            },
        },
    },
}
