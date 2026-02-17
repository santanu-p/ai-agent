# AI Improvement Subsystem

This subsystem implements a full **train/eval/deploy** lifecycle for NPC policies.

## Stages

1. **Collect (`data_collector.py`)**
   - Ingests gameplay telemetry (`player_behavior`, `npc_outcome`, `economy_metric`, `death_cause`, `quest_completion`) into append-only JSONL logs.

2. **Build dataset (`dataset_builder.py`)**
   - Converts raw logs into windowed trajectories and attaches labels/rewards for hybrid imitation + reinforcement training.

3. **Train (`train_policy.py`)**
   - Produces versioned policy artifacts by blending imitation statistics with reward-driven objective signals.

4. **Evaluate (`evaluate_policy.py`)**
   - Enforces promotion gates:
     - fun proxy improvement
     - stability error budget
     - exploit rate ceiling
     - CPU budget limits

5. **Register and rollout (`policy_registry.py`)**
   - Tracks policy metadata, semantic versions, rollout status, canary percentage, promotion, and rollback state.

6. **Deploy in runtime (`policy_runtime_adapter.py`)**
   - Loads promoted/canary policies in NPC decision paths.
   - Performs deterministic cohort assignment for canary traffic.
   - Compares metrics and automatically promotes or rolls back canary policies.

## Canary rollout flow

1. Register candidate policy artifact.
2. Start canary with a small cohort percent.
3. Runtime serves canary policy only to cohort NPC IDs.
4. Record cohort metrics over live traffic.
5. Evaluate against baseline using regression gates.
6. Auto-promote on pass, rollback on failure.
