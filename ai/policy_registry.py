"""Policy registry for versioning and rollout lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PolicyMetadata:
    policy_id: str
    version: str
    artifact_path: str
    metadata: Dict[str, Any]
    rollout_status: str = "registered"


class PolicyRegistry:
    """Persistent registry for policy artifacts and rollout states."""

    def __init__(self, registry_path: str | Path) -> None:
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self.registry_path.write_text(json.dumps({"policies": []}, indent=2), encoding="utf-8")

    def register_policy(
        self,
        policy_id: str,
        version: str,
        artifact_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        doc = self._load()
        entry = {
            "policy_id": policy_id,
            "version": version,
            "artifact_path": artifact_path,
            "metadata": metadata or {},
            "rollout_status": "registered",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        doc["policies"].append(entry)
        self._save(doc)
        return entry

    def start_canary(self, policy_id: str, version: str, cohort_percent: float) -> Dict[str, Any]:
        entry = self._find(policy_id, version)
        entry["rollout_status"] = "canary"
        entry["canary_cohort_percent"] = max(0.0, min(100.0, cohort_percent))
        entry["canary_started_at"] = datetime.now(timezone.utc).isoformat()
        self._update(entry)
        return entry

    def promote(self, policy_id: str, version: str) -> Dict[str, Any]:
        doc = self._load()
        for policy in doc["policies"]:
            if policy["policy_id"] == policy_id:
                policy["rollout_status"] = "archived"
        target = self._find(policy_id, version, doc=doc)
        target["rollout_status"] = "promoted"
        target["promoted_at"] = datetime.now(timezone.utc).isoformat()
        self._save(doc)
        return target

    def rollback(self, policy_id: str, version: str, reason: str) -> Dict[str, Any]:
        entry = self._find(policy_id, version)
        entry["rollout_status"] = "rolled_back"
        entry["rollback_reason"] = reason
        entry["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
        self._update(entry)
        return entry

    def get_promoted(self, policy_id: str) -> Optional[Dict[str, Any]]:
        doc = self._load()
        candidates = [
            item for item in doc["policies"] if item["policy_id"] == policy_id and item["rollout_status"] == "promoted"
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: item["version"])[-1]

    def get_canary(self, policy_id: str) -> Optional[Dict[str, Any]]:
        doc = self._load()
        for item in doc["policies"]:
            if item["policy_id"] == policy_id and item["rollout_status"] == "canary":
                return item
        return None

    def list_policies(self, policy_id: Optional[str] = None) -> List[Dict[str, Any]]:
        doc = self._load()
        if policy_id is None:
            return doc["policies"]
        return [item for item in doc["policies"] if item["policy_id"] == policy_id]

    def _find(self, policy_id: str, version: str, doc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        doc = doc or self._load()
        for item in doc["policies"]:
            if item["policy_id"] == policy_id and item["version"] == version:
                return item
        raise KeyError(f"Policy not found: {policy_id}@{version}")

    def _update(self, updated_entry: Dict[str, Any]) -> None:
        doc = self._load()
        for index, item in enumerate(doc["policies"]):
            if item["policy_id"] == updated_entry["policy_id"] and item["version"] == updated_entry["version"]:
                doc["policies"][index] = updated_entry
                self._save(doc)
                return
        raise KeyError(f"Policy not found: {updated_entry['policy_id']}@{updated_entry['version']}")

    def _load(self) -> Dict[str, Any]:
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def _save(self, doc: Dict[str, Any]) -> None:
        self.registry_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


__all__ = ["PolicyMetadata", "PolicyRegistry"]
