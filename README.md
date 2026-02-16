# AegisWorld Prototype

This repository now includes an executable prototype that turns the 90-day plan into a working baseline runtime:

- Core platform types (`GoalSpec`, `ExecutionPolicy`, `TaskTrace`, `ReflectionRecord`, `SecurityIncident`, `AutonomousChangeSet`)
- Policy engine with budget/latency/tool gates
- Agent kernel loop implementing Plan → Execute → Observe → Reflect → Patch Memory/Policy → Re-plan
- In-memory control/runtime service
- HTTP API surface aligned to the plan endpoints

## Run API server

```bash
python server.py
```

Then call endpoints such as:

- `POST /v1/goals`
- `POST /v1/agents`
- `POST /v1/agents/{agent_id}/execute`
- `GET /v1/goals/{goal_id}`
- `GET /v1/agents/{agent_id}/memory`
- `GET /v1/incidents`
- `POST /v1/policies/simulate`

## Run tests

```bash
python -m pytest -q
```
