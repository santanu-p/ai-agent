from __future__ import annotations

from typing import Dict, Iterable, List

from .models import GateResult, PatchManifest


PATCH_MANIFEST_SCHEMA: Dict[str, object] = {
    "required": {
        "patch_id": str,
        "changed_files": list,
        "changed_domains": list,
        "imported_symbols": list,
        "user_content": str,
        "static_lint_passed": bool,
        "static_typecheck_passed": bool,
        "replay_run_hashes": list,
        "perf_frame_time_ms": (int, float),
        "perf_memory_mb": (int, float),
        "save_from_version": int,
        "save_to_version": int,
        "canary_telemetry": dict,
    }
}


def validate_patch_manifest_schema(manifest: PatchManifest) -> GateResult:
    """Validate that the dataclass payload has required types and shape."""

    required = PATCH_MANIFEST_SCHEMA["required"]
    payload = vars(manifest)
    for field_name, expected_type in required.items():
        if field_name not in payload:
            return GateResult(
                name="schema_validation",
                passed=False,
                reason=f"Missing required field: {field_name}",
            )

        value = payload[field_name]
        if not isinstance(value, expected_type):
            return GateResult(
                name="schema_validation",
                passed=False,
                reason=(
                    f"Field '{field_name}' expected {expected_type} "
                    f"but received {type(value)}"
                ),
            )

    list_fields = ("changed_files", "changed_domains", "imported_symbols", "replay_run_hashes")
    for field_name in list_fields:
        if not all(isinstance(item, str) for item in payload[field_name]):
            return GateResult(
                name="schema_validation",
                passed=False,
                reason=f"Field '{field_name}' must contain only strings.",
            )

    if not all(isinstance(metric_name, str) for metric_name in payload["canary_telemetry"].keys()):
        return GateResult(
            name="schema_validation",
            passed=False,
            reason="Canary telemetry metric names must be strings.",
        )

    if not all(isinstance(value, (int, float)) for value in payload["canary_telemetry"].values()):
        return GateResult(
            name="schema_validation",
            passed=False,
            reason="Canary telemetry metric values must be numeric.",
        )

    return GateResult(name="schema_validation", passed=True, reason="Manifest schema is valid.")
