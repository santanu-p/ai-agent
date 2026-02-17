from __future__ import annotations

import json
import fnmatch
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

DEFAULT_POLICY_FILE = Path("policies/execution_policy.yaml")
DEFAULT_AUDIT_LOG = Path("logs/autonomy_audit.log")


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.startswith("\"") and value.endswith("\""):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _load_simple_yaml(path: Path) -> Dict[str, Any]:
    """Tiny YAML reader for this repository's policy file structure."""
    lines = [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines()]
    root: Dict[str, Any] = {}
    stack: List[tuple[int, Any]] = [(-1, root)]

    for idx, raw in enumerate(lines):
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        text = raw.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if text.startswith("- "):
            value = _parse_scalar(text[2:].strip())
            if not isinstance(parent, list):
                raise ValueError(f"invalid list position: {raw}")
            parent.append(value)
            continue

        key, sep, remainder = text.partition(":")
        if not sep:
            raise ValueError(f"invalid yaml line: {raw}")
        key = key.strip()
        remainder = remainder.strip()

        if remainder:
            if isinstance(parent, dict):
                parent[key] = _parse_scalar(remainder)
            else:
                raise ValueError(f"unexpected scalar mapping: {raw}")
            continue

        next_container: Any
        # Determine list vs map by peeking next non-empty line indent/content.
        next_container = {}
        for candidate in lines[idx + 1 :]:
            if not candidate.strip() or candidate.strip().startswith("#"):
                continue
            cand_indent = len(candidate) - len(candidate.lstrip(" "))
            if cand_indent <= indent:
                break
            next_container = [] if candidate.strip().startswith("- ") else {}
            break

        if isinstance(parent, dict):
            parent[key] = next_container
        else:
            raise ValueError(f"unexpected nested mapping: {raw}")
        stack.append((indent, next_container))

    return root


@dataclass
class ResourceRequest:
    cpu_percent: float
    ram_mb: int
    runtime_seconds: int


@dataclass
class EnforcementDecision:
    allowed: bool
    reason: str


class PolicyGuard:
    """Enforces writable path, network, and resource policy for deployments."""

    def __init__(self, policy_file: Path = DEFAULT_POLICY_FILE):
        self.policy_file = policy_file
        self.policy = self._load_policy()

    def _load_policy(self) -> Dict[str, Any]:
        raw = _load_simple_yaml(self.policy_file)
        return raw.get("execution_policy", {})

    def can_write(self, target_paths: Iterable[str]) -> EnforcementDecision:
        writable = self.policy.get("writable_paths", {})
        allow_patterns = writable.get("allow", [])
        deny_patterns = writable.get("deny", [])

        for path in target_paths:
            normalized = path.strip("/")
            if any(fnmatch.fnmatch(normalized, pattern.strip("/")) for pattern in deny_patterns):
                return EnforcementDecision(False, f"path denied by policy: {path}")
            if not any(fnmatch.fnmatch(normalized, pattern.strip("/")) for pattern in allow_patterns):
                return EnforcementDecision(False, f"path not in allowed writable scope: {path}")
        return EnforcementDecision(True, "writable path policy passed")

    def is_network_allowed(self, hosts: Iterable[str]) -> EnforcementDecision:
        network = self.policy.get("network", {})
        allow_hosts = set(network.get("allow", []))
        deny_hosts = set(network.get("deny", []))

        for host in hosts:
            if host in deny_hosts or "*" in deny_hosts:
                if host not in allow_hosts:
                    return EnforcementDecision(False, f"network host denied by policy: {host}")
            if host not in allow_hosts:
                return EnforcementDecision(False, f"network host not allow-listed: {host}")
        return EnforcementDecision(True, "network policy passed")

    def resources_ok(self, request: ResourceRequest) -> EnforcementDecision:
        limits = self.policy.get("resources", {})
        max_cpu = limits.get("max_cpu_percent", 100)
        max_ram = limits.get("max_ram_mb", 16384)
        max_time = limits.get("max_runtime_seconds", 3600)

        if request.cpu_percent > max_cpu:
            return EnforcementDecision(False, f"cpu limit exceeded ({request.cpu_percent}>{max_cpu})")
        if request.ram_mb > max_ram:
            return EnforcementDecision(False, f"ram limit exceeded ({request.ram_mb}>{max_ram})")
        if request.runtime_seconds > max_time:
            return EnforcementDecision(False, f"runtime limit exceeded ({request.runtime_seconds}>{max_time})")
        return EnforcementDecision(True, "resource limits passed")

    def enforce_pre_deploy(
        self,
        target_paths: Iterable[str],
        hosts: Iterable[str],
        request: ResourceRequest,
    ) -> EnforcementDecision:
        for decision in (
            self.can_write(target_paths),
            self.is_network_allowed(hosts),
            self.resources_ok(request),
        ):
            if not decision.allowed:
                return decision
        return EnforcementDecision(True, "all policy checks passed")


class CircuitBreaker:
    """Stops autonomous improvement loop when failure/regression thresholds are exceeded."""

    def __init__(self, policy: Dict[str, Any], state_file: Path = Path("logs/circuit_breaker_state.json")):
        cfg = policy.get("circuit_breakers", {})
        self.max_failed_deployments = int(cfg.get("max_failed_deployments", 3))
        self.max_regression_threshold = float(cfg.get("max_regression_threshold", 0.2))
        self.disable_file = Path(cfg.get("emergency_disable_file", ".autonomy_disabled"))
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if not self.state_file.exists():
            return {"failed_deployments": 0, "last_regression": 0.0}
        with self.state_file.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save_state(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with self.state_file.open("w", encoding="utf-8") as handle:
            json.dump(self.state, handle, indent=2)

    def is_tripped(self) -> EnforcementDecision:
        if self.disable_file.exists():
            return EnforcementDecision(False, "emergency disable file present")
        if int(self.state.get("failed_deployments", 0)) >= self.max_failed_deployments:
            return EnforcementDecision(False, "max failed deployments reached")
        if float(self.state.get("last_regression", 0.0)) > self.max_regression_threshold:
            return EnforcementDecision(False, "regression threshold exceeded")
        return EnforcementDecision(True, "circuit breaker checks passed")

    def record_success(self, regression_score: float = 0.0) -> None:
        self.state["failed_deployments"] = 0
        self.state["last_regression"] = float(regression_score)
        self._save_state()

    def record_failure(self, regression_score: float) -> None:
        self.state["failed_deployments"] = int(self.state.get("failed_deployments", 0)) + 1
        self.state["last_regression"] = float(regression_score)
        self._save_state()


class AutonomyAuditLogger:
    """Appends JSON-line audit entries for proposed/applied/reverted autonomous changes."""

    def __init__(self, audit_log: Path = DEFAULT_AUDIT_LOG):
        self.audit_log = audit_log
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        self.audit_log.touch(exist_ok=True)

    def log(self, event: str, patch_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "patch_id": patch_id,
            "details": details or {},
        }
        with self.audit_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")


class PatchDeploymentManager:
    """Evaluates guardrails and applies patch callbacks only when policy permits."""

    def __init__(
        self,
        guard: Optional[PolicyGuard] = None,
        logger: Optional[AutonomyAuditLogger] = None,
    ):
        self.guard = guard or PolicyGuard()
        self.logger = logger or AutonomyAuditLogger()
        self.breaker = CircuitBreaker(self.guard.policy)

    def deploy_patch(
        self,
        patch_id: str,
        target_paths: List[str],
        hosts: List[str],
        request: ResourceRequest,
        regression_score: float,
        apply_fn: Callable[[], bool],
    ) -> EnforcementDecision:
        self.logger.log("proposed", patch_id, {"target_paths": target_paths, "hosts": hosts})

        breaker = self.breaker.is_tripped()
        if not breaker.allowed:
            self.logger.log("reverted", patch_id, {"reason": breaker.reason})
            return breaker

        decision = self.guard.enforce_pre_deploy(target_paths, hosts, request)
        if not decision.allowed:
            self.logger.log("reverted", patch_id, {"reason": decision.reason})
            self.breaker.record_failure(regression_score)
            return decision

        applied = apply_fn()
        if applied:
            self.logger.log("applied", patch_id, {"regression_score": regression_score})
            self.breaker.record_success(regression_score)
            return EnforcementDecision(True, "patch deployed")

        self.logger.log("reverted", patch_id, {"reason": "apply_fn returned false"})
        self.breaker.record_failure(regression_score)
        return EnforcementDecision(False, "deployment callback failed")


def read_recent_audit_entries(limit: int = 20, audit_log: Path = DEFAULT_AUDIT_LOG) -> List[Dict[str, Any]]:
    if not audit_log.exists():
        return []
    with audit_log.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()[-limit:]
    return [json.loads(line) for line in lines if line.strip()]


def audit_summary(audit_log: Path = DEFAULT_AUDIT_LOG) -> Dict[str, int]:
    entries = read_recent_audit_entries(limit=1000, audit_log=audit_log)
    summary = {"proposed": 0, "applied": 0, "reverted": 0}
    for entry in entries:
        event = entry.get("event")
        if event in summary:
            summary[event] += 1
    return summary
