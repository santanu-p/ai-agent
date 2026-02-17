import json
import tempfile
import unittest
from pathlib import Path

from tests.simulation import run_simulations


class SimulationScenarioTests(unittest.TestCase):
    def test_run_all_returns_all_scenarios(self):
        results = run_simulations.run_all()
        self.assertEqual(len(results), 5)
        names = {r.name for r in results}
        self.assertSetEqual(
            names,
            {
                "economy_stress_test",
                "combat_difficulty_progression",
                "quest_deadlock_detection",
                "npc_navigation_pathing_robustness",
                "save_load_migration_invariants",
            },
        )

    def test_threshold_evaluation_passes_current_baseline(self):
        baseline = run_simulations.load_baseline(
            Path("tests/simulation/baselines/kpi_baseline.json")
        )
        failures, ok = run_simulations.evaluate_thresholds(run_simulations.run_all(), baseline)
        self.assertTrue(ok)
        self.assertEqual(failures, [])

    def test_artifacts_are_written(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            results = run_simulations.run_all()
            run_simulations.write_artifacts(out, "unit-test", results, failures=[])

            metrics_file = out / "unit-test" / "simulation_metrics.json"
            report_json = out / "unit-test" / "comparison_report.json"
            report_md = out / "unit-test" / "comparison_report.md"

            self.assertTrue(metrics_file.exists())
            self.assertTrue(report_json.exists())
            self.assertTrue(report_md.exists())

            payload = json.loads(report_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "pass")


if __name__ == "__main__":
    unittest.main()
