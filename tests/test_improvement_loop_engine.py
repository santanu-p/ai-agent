from ai.governance import policy_constraints, red_team_tests
from ai.improvement_loop.engine import ImprovementLoopEngine
from ai.improvement_loop.iteration_store import IterationStore
from ai.improvement_loop.objective_evaluator import ObjectiveEvaluator
from ai.improvement_loop.patch_generator import PatchGenerator
from ai.improvement_loop.patch_verifier import PatchVerifier
from ai.improvement_loop.release_manager import ReleaseManager
from ai.improvement_loop.telemetry_collector import SessionEvent, TelemetryCollector


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


def build_engine(tmp_path):
    return ImprovementLoopEngine(
        telemetry_collector=TelemetryCollector(),
        objective_evaluator=ObjectiveEvaluator(),
        patch_generator=PatchGenerator(model_client=FakeModelClient(), prompt_version="v2"),
        patch_verifier=PatchVerifier(
            static_checks=["python -c \"print('static ok')\""],
            simulation_checks=["python -c \"print('sim ok')\""],
        ),
        release_manager=ReleaseManager(),
        iteration_store=IterationStore(root=str(tmp_path)),
    )


def test_engine_iteration_persists_governance_artifact(tmp_path):
    engine = build_engine(tmp_path)
    events = [
        SessionEvent("s1", day_retained=7, quest_completed=True, death_cause="fall", economy_delta_pct=0.01),
        SessionEvent("s2", day_retained=1, quest_completed=False, death_cause="fall", economy_delta_pct=0.02),
    ]

    result = engine.run_iteration(
        iteration_id="iter-e-001",
        telemetry_inputs={"events": events},
        previous_stable_version="release-99",
        declared_constraint_ids=[
            constraint.id for constraint in policy_constraints.NON_NEGOTIABLE_CONSTRAINTS
        ],
        risk_categories=[policy_constraints.RiskCategory.CONTENT_TUNING],
        red_team_scenario_ids=red_team_tests.scenario_ids(red_team_tests.RED_TEAM_SCENARIOS),
    )

    assert result.governance.approved is True
    artifact = (tmp_path / "iter-e-001.json").read_text(encoding="utf-8")
    assert '"governance_verdict"' in artifact
    assert '"approved": true' in artifact


def test_engine_rejects_high_risk_without_human_approval(tmp_path):
    engine = build_engine(tmp_path)
    events = [
        SessionEvent("s1", day_retained=7, quest_completed=True, death_cause="fall", economy_delta_pct=0.00),
        SessionEvent("s2", day_retained=7, quest_completed=True, death_cause="fall", economy_delta_pct=0.00),
    ]

    result = engine.run_iteration(
        iteration_id="iter-e-002",
        telemetry_inputs={"events": events},
        previous_stable_version="release-99",
        declared_constraint_ids=[
            constraint.id for constraint in policy_constraints.NON_NEGOTIABLE_CONSTRAINTS
        ],
        risk_categories=[policy_constraints.RiskCategory.ECONOMY_REWRITE],
        human_approval_granted=False,
        red_team_scenario_ids=red_team_tests.scenario_ids(red_team_tests.RED_TEAM_SCENARIOS),
    )

    assert result.governance.requires_human_approval is True
    assert result.rollout.decision == "reject"
    assert "Governance gate failed" in result.rollout.reason
