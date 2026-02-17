# Improvement Loop Components

This package implements an iterative optimization loop for live gameplay tuning.

## Components

- `telemetry_collector`: aggregates gameplay metrics including retention proxies, quest completion, death causes, and economy inflation.
- `objective_evaluator`: computes objective-level and aggregate fitness scores.
- `patch_generator`: asks an LLM for constrained config/code patch diffs.
- `patch_verifier`: executes static checks and simulation test commands.
- `release_manager`: supports canary rollout decisions to a fraction of sessions.

## Iteration storage

Each iteration is persisted as JSON by `IterationStore` in `ai/improvement_loop/iterations/<iteration_id>.json` with:

- input metrics snapshot,
- prompt/version,
- proposed diff,
- verification results,
- rollout decision and rollback pointer.
