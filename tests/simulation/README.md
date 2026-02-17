# Simulation Test Suite

This folder contains deterministic, automated simulation scenarios for validating every proposed AI patch before deployment.

## Scenarios covered

- Economy stress test
- Combat difficulty progression
- Quest deadlock detection
- NPC navigation/pathing robustness
- Save/load migration invariants

## Local execution

```bash
python3 tests/simulation/run_simulations.py --patch-version local
```

Artifacts are generated in `artifacts/simulation/`:

- `results-<patch-version>.json`
- `report-<patch-version>.md`

The script exits non-zero if any KPI threshold fails, which makes it suitable as a CI deployment gate.
