# AegisWorld

AegisWorld is an autonomous agentic platform scaffold with:

- TypeScript control plane API.
- Python runtime plane (agent kernel).
- Python learning plane (reflection, failure clustering, policy tuning).
- Python security plane (incident ingestion and remediation actions).
- Shared API contracts and architecture docs.
- Kubernetes and Terraform starter artifacts for AWS multi-region deployment.

## Monorepo layout

```text
apps/
  control-plane/
  web-console/
services/
  runtime-plane/
  learning-plane/
  security-plane/
contracts/
infra/
docs/
```

## Quick start

### Control plane

```bash
cd apps/control-plane
npm install
npm run dev
```

On Windows PowerShell with script execution restrictions, use:

```powershell
npm.cmd install
npm.cmd run dev
```

### Runtime/Learning/Security planes

```bash
cd services/runtime-plane
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8101
```

Repeat for `services/learning-plane` (port `8102`) and `services/security-plane` (port `8103`).

### Web console

```bash
cd apps/web-console
npm install
npm run dev
```

## Local full stack

```bash
docker compose up --build
```

## Smoke test

After services are running:

```powershell
./scripts/smoke.ps1
```

## Included APIs

- `POST /v1/goals`
- `GET /v1/goals/{goal_id}`
- `POST /v1/agents`
- `POST /v1/agents/{agent_id}/execute`
- `GET /v1/agents/{agent_id}/memory`
- `POST /v1/domain/social/projects`
- `POST /v1/domain/games/projects`
- `POST /v1/domain/dev/pipelines`
- `GET /v1/incidents`
- `POST /v1/policies/simulate`
- `POST /v1/deployments/changesets`
- `POST /v1/deployments/changesets/{change_id}/promote`

## Status

This repository is an implementation-grade foundation, not a full 90-day finished product.
It includes core execution loops, contracts, policy simulation, reflection workflows,
domain-pack routing, incident remediation primitives, and deployment scaffolding.
