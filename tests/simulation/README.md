# Simulation Suite

This folder contains automated simulation scenarios used to gate AI patches.

## Scenarios

- Economy stress test (`economy_stress_test`)
- Combat difficulty progression (`combat_difficulty_progression`)
- Quest deadlock detection (`quest_deadlock_detection`)
- NPC navigation/pathing robustness (`npc_navigation_pathing_robustness`)
- Save/load migration invariants (`save_load_migration_invariants`)

## Running locally

```bash
python tests/simulation/run_simulations.py --version local
python -m unittest tests.simulation.test_simulations
```

## KPI gating behavior

- KPI thresholds are defined in `tests/simulation/baselines/kpi_baseline.json`.
- CI fails when any metric falls outside threshold bounds.
- Each patch version writes artifacts to `artifacts/simulations/<version>/`:
  - `simulation_metrics.json`
  - `comparison_report.json`
  - `comparison_report.md`

In GitHub Actions, `<version>` is the patch commit SHA (`github.sha`) so each proposed patch has archived simulation and comparison records.
