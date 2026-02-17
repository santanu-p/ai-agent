# AegisWorld Architecture

## Planes

- **Control plane (TypeScript)**: API surface, orchestration, policy simulation, model routing.
- **Deployment controller (inside control plane)**: autonomous change-set staging, canary evaluation, and progressive promotion.
- **Runtime plane (Python)**: agent kernel loop (`Plan -> Execute -> Observe -> Reflect -> Patch -> Re-plan`).
- **Learning plane (Python)**: failure clustering, reflection synthesis, policy and memory patch recommendation.
- **Security plane (Python)**: incident ingestion, blast-radius estimation, autonomous remediation actions.

## Data flow

1. User sends `GoalSpec` to control plane.
2. Goal router assigns domain pack and execution envelope.
3. Orchestrator dispatches to runtime plane.
4. Runtime plane executes tools and models under policy envelope.
5. Trace events stream to learning and security planes.
6. Learning emits `ReflectionRecord` and patch recommendations.
7. Security emits `SecurityIncident` and remediation status.
8. Control plane exposes outcomes and simulation endpoints.

## Non-goals in this scaffold

- Full AWS account bootstrap automation.
- Production-ready multi-region data replication.
- Real credential rotation against cloud providers.
- Full zero-trust policy proofs.
