from pathlib import Path
from .engine import AIPatchEnforcer
from .models import EnforcementReport, GateResult, PatchContext
from .schema import SchemaValidationError, validate_policy_schema

_FALLBACK_POLICY={
    "allowed_path_prefixes":["ai"],"allowed_config_domains":["policy"],"forbidden_apis":[],"lint_commands":[],"typecheck_commands":[],"replay_seed":0,
    "performance_budget":{"frame_time_ms_p95_max":1e9,"memory_mb_peak_max":1e9},
    "canary_thresholds":{"max_error_rate":1e9,"max_p95_latency_ms":1e9,"max_timeout_rate":1e9},
    "save_compatibility":{"required_keys":["version"],"allowed_version_range":[0,9999]},
}

def enforce_patch(policy_payload: dict, context: PatchContext) -> EnforcementReport:
    try:
        policy=validate_policy_schema(policy_payload)
        report=AIPatchEnforcer(policy).enforce(context)
        report.gate_results.insert(0,GateResult("schema_validation",True,"Policy schema validated"))
        return report
    except SchemaValidationError as exc:
        enforcer=AIPatchEnforcer(validate_policy_schema(_FALLBACK_POLICY))
        report=enforcer.enforce(context)
        report.gate_results.insert(0,GateResult("schema_validation",False,str(exc)))
        if not report.quarantined:
            enforcer._auto_revert(context.repo_path)
            report.quarantine_record=enforcer._write_quarantine(context.patch_id, report.gate_results)
            report.quarantined=True
        return report

__all__=["AIPatchEnforcer","EnforcementReport","PatchContext","SchemaValidationError","enforce_patch","validate_policy_schema"]
