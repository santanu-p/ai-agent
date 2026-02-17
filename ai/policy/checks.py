from __future__ import annotations

from typing import Iterable, Sequence

from .models import GateResult, PatchManifest, PolicyConfig


def allowed_modification_check(manifest: PatchManifest, config: PolicyConfig) -> GateResult:
    for path in manifest.changed_files:
        if not any(path.startswith(prefix) for prefix in config.allowed_file_prefixes):
            return GateResult(
                name="allowed_modification_policy",
                passed=False,
                reason=f"File '{path}' is outside allowed prefixes.",
            )

    forbidden_domains = [d for d in manifest.changed_domains if d not in config.allowed_domains]
    if forbidden_domains:
        return GateResult(
            name="allowed_modification_policy",
            passed=False,
            reason=f"Forbidden config domains changed: {', '.join(forbidden_domains)}",
        )

    return GateResult(
        name="allowed_modification_policy",
        passed=True,
        reason="Changed files and domains are authorized.",
    )


def forbidden_api_check(manifest: PatchManifest, config: PolicyConfig) -> GateResult:
    used_forbidden = sorted(set(manifest.imported_symbols).intersection(config.forbidden_apis))
    if used_forbidden:
        return GateResult(
            name="forbidden_api_check",
            passed=False,
            reason=f"Forbidden APIs imported: {', '.join(used_forbidden)}",
        )

    return GateResult(name="forbidden_api_check", passed=True, reason="No forbidden APIs detected.")


def static_analysis_gate(manifest: PatchManifest) -> GateResult:
    if not manifest.static_lint_passed:
        return GateResult(name="static_analysis_gate", passed=False, reason="Static lint checks failed.")
    if not manifest.static_typecheck_passed:
        return GateResult(name="static_analysis_gate", passed=False, reason="Static type checks failed.")
    return GateResult(name="static_analysis_gate", passed=True, reason="Static lint/type checks passed.")


def deterministic_replay_gate(manifest: PatchManifest) -> GateResult:
    hashes = manifest.replay_run_hashes
    if not hashes:
        return GateResult(name="deterministic_replay_gate", passed=False, reason="No replay hashes provided.")

    unique_hashes = set(hashes)
    if len(unique_hashes) > 1:
        return GateResult(
            name="deterministic_replay_gate",
            passed=False,
            reason="Replay hashes diverged; execution is non-deterministic.",
        )

    return GateResult(name="deterministic_replay_gate", passed=True, reason="Replay hashes are deterministic.")


def save_compatibility_gate(manifest: PatchManifest, config: PolicyConfig) -> GateResult:
    compatibility = config.save_compatibility
    if manifest.save_from_version < compatibility.minimum_supported_version:
        return GateResult(
            name="save_compatibility_gate",
            passed=False,
            reason=(
                "Patch drops backward compatibility: "
                f"source version {manifest.save_from_version} < "
                f"minimum supported {compatibility.minimum_supported_version}."
            ),
        )

    if manifest.save_to_version != compatibility.current_version:
        return GateResult(
            name="save_compatibility_gate",
            passed=False,
            reason=(
                f"Patch save target version {manifest.save_to_version} "
                f"must match current version {compatibility.current_version}."
            ),
        )

    return GateResult(
        name="save_compatibility_gate",
        passed=True,
        reason="Backward save-load compatibility preserved.",
    )


def performance_budget_gate(manifest: PatchManifest, config: PolicyConfig) -> GateResult:
    budget = config.performance_budget
    if manifest.perf_frame_time_ms > budget.max_frame_time_ms:
        return GateResult(
            name="performance_budget_gate",
            passed=False,
            reason=(
                f"Frame time {manifest.perf_frame_time_ms}ms exceeds "
                f"budget {budget.max_frame_time_ms}ms."
            ),
        )

    if manifest.perf_memory_mb > budget.max_memory_mb:
        return GateResult(
            name="performance_budget_gate",
            passed=False,
            reason=(
                f"Memory {manifest.perf_memory_mb}MB exceeds "
                f"budget {budget.max_memory_mb}MB."
            ),
        )

    return GateResult(name="performance_budget_gate", passed=True, reason="Performance budgets satisfied.")


def prompt_injection_security_gate(manifest: PatchManifest, config: PolicyConfig) -> GateResult:
    lowered = manifest.user_content.lower()
    suspicious = [marker for marker in config.prompt_injection_markers if marker.lower() in lowered]
    if suspicious:
        return GateResult(
            name="prompt_injection_security_gate",
            passed=False,
            reason=f"Potential prompt-injection markers found: {', '.join(suspicious)}",
        )

    return GateResult(
        name="prompt_injection_security_gate",
        passed=True,
        reason="No prompt-injection markers found in user content.",
    )


def canary_telemetry_gate(manifest: PatchManifest, config: PolicyConfig) -> GateResult:
    telemetry = manifest.canary_telemetry
    for threshold in config.telemetry_gates:
        if threshold.metric_name not in telemetry:
            return GateResult(
                name="canary_telemetry_gate",
                passed=False,
                reason=f"Missing canary metric: {threshold.metric_name}",
            )

        value = telemetry[threshold.metric_name]
        if value > threshold.max_allowed_value:
            return GateResult(
                name="canary_telemetry_gate",
                passed=False,
                reason=(
                    f"Canary metric '{threshold.metric_name}'={value} "
                    f"exceeds threshold {threshold.max_allowed_value}."
                ),
            )

    return GateResult(name="canary_telemetry_gate", passed=True, reason="Canary telemetry is within thresholds.")
