from ai.governance import policy_constraints, red_team_tests
from ai.improvement_loop import (
    ImprovementLoop,
    IterationStore,
    ObjectiveEvaluator,
    PatchGenerator,
    PatchVerifier,
    ReleaseManager,
    SessionEvent,
    TelemetryCollector,
)


class FakeModelClient:
    def complete(self, prompt: str) -> str:
        assert "Constraints:" in prompt
        return """diff --git a/gameplay/config.yaml b/gameplay/config.yaml
--- a/gameplay/config.yaml
+++ b/gameplay/config.yaml
@@ -1,2 +1,2 @@
-drop_rate: 0.10
+drop_rate: 0.08
"""


def test_improvement_loop_writes_iteration(tmp_path):
    store = IterationStore(root=tmp_path)
    loop = ImprovementLoop(
        telemetry_collector=TelemetryCollector(),
        objective_evaluator=ObjectiveEvaluator(),
        patch_generator=PatchGenerator(model_client=FakeModelClient(), prompt_version="v2"),
        patch_verifier=PatchVerifier(
            static_checks=["python -c \"print('static ok')\""],
            simulation_checks=["python -c \"print('sim ok')\""],
        ),
        release_manager=ReleaseManager(),
        iteration_store=store,
    )

    events = [
        SessionEvent("s1", day_retained=7, quest_completed=True, death_cause="fall", economy_delta_pct=0.01),
        SessionEvent("s2", day_retained=1, quest_completed=False, death_cause="fall", economy_delta_pct=0.02),
        SessionEvent("s3", day_retained=0, quest_completed=True, death_cause="boss", economy_delta_pct=0.00),
    ]

    record = loop.run_iteration(
        "iter-001",
        events,
        previous_stable_version="release-42",
        declared_constraint_ids=[
            constraint.id for constraint in policy_constraints.NON_NEGOTIABLE_CONSTRAINTS
        ],
        risk_categories=[policy_constraints.RiskCategory.CONTENT_TUNING],
        human_approval_granted=False,
        red_team_scenario_ids=red_team_tests.scenario_ids(red_team_tests.RED_TEAM_SCENARIOS),
    )

    assert record.iteration_id == "iter-001"
    assert record.prompt_version == "v2"
    assert "gameplay/config.yaml" in record.proposed_diff
    assert record.verification_results.passed is True
    assert record.governance_verdict.approved is True
    assert record.rollout_decision.rollback_pointer == "release-42"

    saved = store.load("iter-001")
    assert saved.input_metrics_snapshot.active_sessions == 3
    assert saved.input_metrics_snapshot.top_death_causes["fall"] == 2
    assert saved.governance_verdict.approved is True


def test_improvement_loop_blocks_release_without_required_human_approval(tmp_path):
    store = IterationStore(root=tmp_path)
    loop = ImprovementLoop(
        telemetry_collector=TelemetryCollector(),
        objective_evaluator=ObjectiveEvaluator(),
        patch_generator=PatchGenerator(model_client=FakeModelClient(), prompt_version="v2"),
        patch_verifier=PatchVerifier(
            static_checks=["python -c \"print('static ok')\""],
            simulation_checks=["python -c \"print('sim ok')\""],
        ),
        release_manager=ReleaseManager(),
        iteration_store=store,
    )

    events = [
        SessionEvent("s1", day_retained=7, quest_completed=True, death_cause="fall", economy_delta_pct=0.0),
        SessionEvent("s2", day_retained=7, quest_completed=True, death_cause="fall", economy_delta_pct=0.0),
    ]

    record = loop.run_iteration(
        "iter-002",
        events,
        previous_stable_version="release-42",
        declared_constraint_ids=[
            constraint.id for constraint in policy_constraints.NON_NEGOTIABLE_CONSTRAINTS
        ],
        risk_categories=[policy_constraints.RiskCategory.ECONOMY_REWRITE],
        human_approval_granted=False,
        red_team_scenario_ids=red_team_tests.scenario_ids(red_team_tests.RED_TEAM_SCENARIOS),
    )

    assert record.governance_verdict.requires_human_approval is True
    assert record.governance_verdict.approved is False
    assert record.rollout_decision.decision == "reject"
    assert "Governance gate failed" in record.rollout_decision.reason
