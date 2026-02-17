from dataclasses import dataclass

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
from ai.improvement_loop.engine import ImprovementLoopEngine
from ai.improvement_loop.models import GeneratedPatch, PatchProposal, VerificationResults


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

    record = loop.run_iteration("iter-001", events, previous_stable_version="release-42")

    assert record.iteration_id == "iter-001"
    assert record.prompt_version == "v2"
    assert "gameplay/config.yaml" in record.proposed_diff
    assert record.verification_results.passed is True
    assert record.rollout_decision.rollback_pointer == "release-42"

    saved = store.load("iter-001")
    assert saved.input_metrics_snapshot.active_sessions == 3
    assert saved.input_metrics_snapshot.top_death_causes["fall"] == 2


@dataclass
class _Rollout:
    decision: str


class _Telemetry:
    def collect(self, **telemetry_inputs):
        return telemetry_inputs["snapshot"]


class _Objective:
    def evaluate(self, snapshot):
        return {"fitness": snapshot["score"]}


class _Generator:
    def __init__(self, proposal):
        self.proposal = proposal

    def propose_patch(self, snapshot, fitness, constraints, target_files):
        return self.proposal


class _Verifier:
    def __init__(self, passed: bool):
        self.received_patch = None
        self.result = VerificationResults(
            static_checks_passed=passed,
            simulation_checks_passed=passed,
            static_check_report="ok" if passed else "fail",
            simulation_report="ok" if passed else "fail",
        )

    def verify(self, patch):
        self.received_patch = patch
        return self.result


class _ReleaseManager:
    def decide(self, **kwargs):
        if kwargs["verification"].passed:
            return _Rollout(decision="canary")
        return _Rollout(decision="reject")


class _Store:
    def store(self, **kwargs):
        return "artifact.json"


def test_engine_run_iteration_passes_generated_patch_to_verifier():
    proposal = GeneratedPatch(
        prompt_version="v1",
        prompt_text="prompt",
        diff="diff --git a/a b/a",
        target_files=["a"],
    )
    verifier = _Verifier(passed=True)
    engine = ImprovementLoopEngine(
        telemetry_collector=_Telemetry(),
        objective_evaluator=_Objective(),
        patch_generator=_Generator(proposal),
        patch_verifier=verifier,
        release_manager=_ReleaseManager(),
        iteration_store=_Store(),
    )

    result = engine.run_iteration(
        iteration_id="it-1",
        telemetry_inputs={"snapshot": {"score": 0.9}},
        constraints=["small"],
        target_files=["a"],
        candidate_revision="cand",
        stable_revision="stable",
        requested_canary_fraction=0.1,
    )

    assert verifier.received_patch is proposal
    assert result.verification.passed is True
    assert result.rollout.decision == "canary"


def test_engine_run_iteration_maps_patch_proposal_for_verifier_rejection_path():
    proposal = PatchProposal(
        prompt_version="v1",
        prompt="prompt",
        proposed_diff="diff --git a/a b/a",
        target_files=["a"],
    )
    verifier = _Verifier(passed=False)
    engine = ImprovementLoopEngine(
        telemetry_collector=_Telemetry(),
        objective_evaluator=_Objective(),
        patch_generator=_Generator(proposal),
        patch_verifier=verifier,
        release_manager=_ReleaseManager(),
        iteration_store=_Store(),
    )

    result = engine.run_iteration(
        iteration_id="it-2",
        telemetry_inputs={"snapshot": {"score": 0.1}},
        constraints=["small"],
        target_files=["a"],
        candidate_revision="cand",
        stable_revision="stable",
        requested_canary_fraction=0.1,
    )

    assert isinstance(verifier.received_patch, GeneratedPatch)
    assert verifier.received_patch.prompt_text == proposal.prompt
    assert result.verification.passed is False
    assert result.rollout.decision == "reject"
