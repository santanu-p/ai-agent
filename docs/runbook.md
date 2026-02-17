# Operations Runbook (Scaffold)

## Deploy

1. Build images for control/runtime/learning/security planes.
2. Push images to registry.
3. Apply namespace and service manifests in `infra/k8s`.
4. Verify `/healthz` endpoints.

## Incident response

1. Ingest incident into security plane.
2. Run remediation endpoint for selected incident.
3. Validate verification state is `completed`.
4. Mirror incident outcome into control-plane `/v1/incidents`.

## Policy update workflow

1. Generate candidate policy patch from learning plane.
2. Simulate with `/v1/policies/simulate`.
3. Promote only if recommendation is `approve`.

