# AegisWorld Prototype

This repository includes an executable prototype that turns the 90-day plan into a working baseline runtime:

- Core platform types (`GoalSpec`, `ExecutionPolicy`, `TaskTrace`, `ReflectionRecord`, `SecurityIncident`, `AutonomousChangeSet`)
- Policy engine with budget/latency/tool gates
- Agent kernel loop implementing Plan → Execute → Observe → Reflect → Patch Memory/Policy → Re-plan
- Learning engine for reflection clustering and memory compaction
- In-memory control/runtime service with JSON snapshot persistence
- Goal status tracking and autonomous scheduler queue
- HTTP API surface aligned to and expanding on the plan endpoints

## Run API server

```bash
python server.py
```

### Main endpoints

- `POST /v1/goals`
- `GET /v1/goals/{goal_id}`
- `POST /v1/agents`
- `GET /v1/agents/{agent_id}`
- `POST /v1/agents/{agent_id}/execute`
- `POST /v1/agents/{agent_id}/policy`
- `GET /v1/agents/{agent_id}/memory`
- `POST /v1/domain/social/projects`
- `POST /v1/domain/dev/pipelines`
- `POST /v1/domain/games/projects`
- `GET /v1/incidents`
- `POST /v1/policies/simulate`
- `POST /v1/scheduler/assign`
- `POST /v1/scheduler/run`
- `GET /v1/scheduler/queue`
- `GET /v1/traces`
- `GET /v1/reflections`
- `GET /v1/changes`
- `GET /v1/learning/summary`
- `POST /v1/learning/compact?agent_id=...&max_items=...`
- `GET /v1/stats`
- `GET /healthz`

## Run tests

```bash
python -m pytest -q
```
