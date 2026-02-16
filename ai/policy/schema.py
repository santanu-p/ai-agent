from __future__ import annotations
from typing import Any
from .models import AIPolicy, CanaryThresholds, PerformanceBudget, SaveCompatibilityRule

class SchemaValidationError(ValueError):
    pass

def _req(d: dict[str, Any], keys: tuple[str, ...]) -> None:
    m=[k for k in keys if k not in d]
    if m: raise SchemaValidationError(f"Missing required keys: {', '.join(m)}")

def _strs(v: Any, key: str) -> tuple[str,...]:
    if not isinstance(v,(list,tuple)) or not all(isinstance(x,str) and x for x in v):
        raise SchemaValidationError(f"{key} must be a list of non-empty strings")
    return tuple(v)

def _num(v: Any, key: str) -> float:
    if not isinstance(v,(int,float)): raise SchemaValidationError(f"{key} must be numeric")
    return float(v)

def validate_policy_schema(payload: dict[str, Any]) -> AIPolicy:
    _req(payload,("allowed_path_prefixes","allowed_config_domains","forbidden_apis","lint_commands","typecheck_commands","replay_seed","performance_budget","canary_thresholds","save_compatibility"))
    pb=payload["performance_budget"]; ct=payload["canary_thresholds"]; sc=payload["save_compatibility"]
    _req(pb,("frame_time_ms_p95_max","memory_mb_peak_max")); _req(ct,("max_error_rate","max_p95_latency_ms","max_timeout_rate")); _req(sc,("required_keys","allowed_version_range"))
    avr=sc["allowed_version_range"]
    if not isinstance(avr,(list,tuple)) or len(avr)!=2 or not all(isinstance(x,int) for x in avr):
        raise SchemaValidationError("save_compatibility.allowed_version_range must be two integers")
    return AIPolicy(
        allowed_path_prefixes=_strs(payload["allowed_path_prefixes"],"allowed_path_prefixes"),
        allowed_config_domains=_strs(payload["allowed_config_domains"],"allowed_config_domains"),
        forbidden_apis=_strs(payload["forbidden_apis"],"forbidden_apis"),
        lint_commands=_strs(payload["lint_commands"],"lint_commands"),
        typecheck_commands=_strs(payload["typecheck_commands"],"typecheck_commands"),
        replay_seed=int(payload["replay_seed"]),
        performance_budget=PerformanceBudget(_num(pb["frame_time_ms_p95_max"],"frame"),_num(pb["memory_mb_peak_max"],"memory")),
        canary_thresholds=CanaryThresholds(_num(ct["max_error_rate"],"error"),_num(ct["max_p95_latency_ms"],"latency"),_num(ct["max_timeout_rate"],"timeout")),
        save_compatibility=SaveCompatibilityRule(_strs(sc["required_keys"],"required_keys"),(avr[0],avr[1])),
    )
