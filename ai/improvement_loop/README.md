# Improvement Loop

This package provides a telemetry-driven iterative improvement loop with the following components:

- `telemetry_collector`: captures gameplay metrics such as retention proxies, quest completion, death causes, and economy inflation.
- `objective_evaluator`: computes weighted fitness scores from a metrics snapshot.
- `patch_generator`: asks a model client to produce constrained config/code diffs.
- `patch_verifier`: runs static checks and simulation tests for candidate patches.
- `release_manager`: approves/rejects canary rollout to a fraction of sessions and records rollback pointers.
- `iteration_store`: persists each iteration artifact as JSON under `ai/improvement_loop/iterations/`.

## Stored iteration fields

Each iteration JSON record includes:

1. Input metrics snapshot,
2. Prompt/version,
3. Proposed diff,
4. Verification results,
5. Rollout decision and rollback pointer.
