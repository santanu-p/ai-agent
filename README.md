# AegisWorld

AegisWorld is a multi-plane autonomous systems scaffold designed for contributors who need to build, test, and operate agentic services quickly. The repository combines a TypeScript control plane, Python service planes, shared contracts, and deployment scaffolding.

## Architecture at a glance

AegisWorld is organized into four planes:

- **Control plane (TypeScript):** API surface, orchestration, policy simulation, and model routing.
- **Runtime plane (Python):** agent kernel execution loop (`Plan -> Execute -> Observe -> Reflect -> Patch -> Re-plan`).
- **Learning plane (Python):** failure clustering, reflection synthesis, and patch recommendations.
- **Security plane (Python):** incident ingestion, blast-radius estimation, and remediation actions.

For deeper details, see `docs/architecture.md`.

## Monorepo layout

```text
apps/
  control-plane/      # Fastify + TypeScript API/orchestration
  web-console/        # React + Vite UI
services/
  runtime-plane/      # Runtime service (FastAPI)
  learning-plane/     # Learning service (FastAPI)
  security-plane/     # Security service (FastAPI)
contracts/
  openapi.yaml        # Shared API contract
infra/                # Terraform + Kubernetes scaffolding
docs/                 # Architecture, runbook, SLO targets
scripts/              # Local tooling, smoke checks
```

## Prerequisites

- **Node.js 22** (npm included)
- **Python 3.12**
- **Docker + Docker Compose** (optional, for full-stack local bring-up)

## Quick start

### 1) Install workspace dependencies

From repository root:

```bash
npm ci
```

### 2) Start control plane

```bash
npm run -w apps/control-plane dev
```

PowerShell fallback when script execution blocks `npm`:

```powershell
npm.cmd run -w apps/control-plane dev
```

### 3) Start runtime plane

```bash
cd services/runtime-plane
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8101
```

### 4) Start learning plane

```bash
cd services/learning-plane
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8102
```

### 5) Start security plane

```bash
cd services/security-plane
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8103
```

### 6) Start web console

```bash
npm run -w apps/web-console dev
```

## Running tests locally

### Control plane

```bash
npm run -w apps/control-plane test
```

### Python services

Run per service:

```bash
cd services/runtime-plane
python -m pip install -r requirements.txt
PYTHONPATH=. python -m pytest -q tests
```

```bash
cd services/learning-plane
python -m pip install -r requirements.txt
PYTHONPATH=. python -m pytest -q tests
```

```bash
cd services/security-plane
python -m pip install -r requirements.txt
PYTHONPATH=. python -m pytest -q tests
```

## CI overview

The `ci` workflow validates:

- **Node workspace install and control-plane tests** using root `npm ci` and workspace test execution.
- **Python service matrix tests** for `runtime-plane`, `learning-plane`, and `security-plane` using interpreter-scoped commands (`python -m ...`).

Simulation workflows are intentionally separate and unchanged in this pass.

## Full stack with Docker

```bash
docker compose up --build
```

## Smoke test

With local services running:

```powershell
./scripts/smoke.ps1
```

## API references

Primary contract: `contracts/openapi.yaml`

Common endpoints include:

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

## Operational docs

- Architecture: `docs/architecture.md`
- Operations runbook: `docs/runbook.md`
- SLO targets: `docs/slo.md`

## Troubleshooting

- **PowerShell cannot execute npm scripts:** use `npm.cmd` variants.
- **Python import/test issues in services:** ensure Python `3.12`, dependencies installed from each service folder, and set `PYTHONPATH=.` for test runs.
- **Common CI failure (`npm ci` lockfile errors):** run `npm install` at repository root to refresh `package-lock.json`, then re-run `npm ci`.
- **Common CI failure (pytest invocation mismatch):** run tests with `python -m pytest -q tests` instead of bare `pytest`.
