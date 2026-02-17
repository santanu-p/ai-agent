from game.ai import (
    AIPatch,
    AdaptiveAILoop,
    DeltaOperation,
    KPIReadings,
    KPIThresholds,
    PatchValidator,
    RuntimeStats,
    SimulationResult,
)


def test_happy_path_deploy_and_no_rollback():
    validator = PatchValidator(thresholds=KPIThresholds())
    loop = AdaptiveAILoop(validator=validator)

    baseline = KPIReadings(0.70, 16.0, 0.75)
    candidate = KPIReadings(0.72, 15.5, 0.78)
    patch = AIPatch.new(
        patch_id="patch-001",
        rationale="Improve dialogue pacing.",
        deltas=[DeltaOperation(scope="behavior", target="npc.dialogue.cooldown", op="decrement", value=0.2)],
    )

    deployed, _ = loop.run_cycle(
        observed_baseline=baseline,
        proposed_patch=patch,
        evaluated_candidate=candidate,
        simulation_results=[SimulationResult("quest_critical_path", success=True)],
        runtime_stats=RuntimeStats(cpu_ms_per_tick=2.5, memory_mb=64.0),
    )
    assert deployed is True

    rolled_back, _ = loop.monitor_and_rollback(post_deploy_kpis=KPIReadings(0.72, 15.7, 0.77))
    assert rolled_back is False


def test_validation_rejects_exploit_target():
    validator = PatchValidator(thresholds=KPIThresholds())
    loop = AdaptiveAILoop(validator=validator)

    baseline = KPIReadings(0.70, 16.0, 0.75)
    candidate = KPIReadings(0.71, 16.2, 0.74)
    bad_patch = AIPatch.new(
        patch_id="patch-unsafe",
        rationale="Unsafe test",
        deltas=[DeltaOperation(scope="policy", target="auth.permissions", op="set", value={"gm": "all"})],
    )

    deployed, message = loop.run_cycle(
        observed_baseline=baseline,
        proposed_patch=bad_patch,
        evaluated_candidate=candidate,
        simulation_results=[SimulationResult("quest_critical_path", success=True)],
        runtime_stats=RuntimeStats(cpu_ms_per_tick=2.0, memory_mb=32.0),
    )

    assert deployed is False
    assert "exploit/safety" in message


def test_auto_rollback_on_kpi_regression():
    validator = PatchValidator(thresholds=KPIThresholds(), max_allowed_regression_ratio=0.05)
    loop = AdaptiveAILoop(validator=validator)

    baseline_v1 = KPIReadings(0.70, 16.0, 0.75)
    candidate_v1 = KPIReadings(0.71, 15.8, 0.76)
    patch_v1 = AIPatch.new(
        patch_id="patch-001",
        rationale="First deploy",
        deltas=[DeltaOperation(scope="behavior", target="npc.greeting.weight", op="increment", value=0.1)],
    )
    assert loop.run_cycle(
        observed_baseline=baseline_v1,
        proposed_patch=patch_v1,
        evaluated_candidate=candidate_v1,
        simulation_results=[SimulationResult("quest_critical_path", success=True)],
        runtime_stats=RuntimeStats(cpu_ms_per_tick=2.0, memory_mb=32.0),
    )[0]

    baseline_v2 = candidate_v1
    candidate_v2 = KPIReadings(0.73, 15.2, 0.78)
    patch_v2 = AIPatch.new(
        patch_id="patch-002",
        parent_patch_id="patch-001",
        rationale="Second deploy",
        deltas=[DeltaOperation(scope="policy", target="quest.hint_frequency", op="increment", value=1)],
    )
    assert loop.run_cycle(
        observed_baseline=baseline_v2,
        proposed_patch=patch_v2,
        evaluated_candidate=candidate_v2,
        simulation_results=[SimulationResult("quest_critical_path", success=True)],
        runtime_stats=RuntimeStats(cpu_ms_per_tick=2.0, memory_mb=32.0),
    )[0]

    rolled_back, message = loop.monitor_and_rollback(post_deploy_kpis=KPIReadings(0.64, 17.0, 0.70))
    assert rolled_back is True
    assert "Auto-reverted" in message
    assert loop.ledger.active.patch.patch_id == "patch-001"
