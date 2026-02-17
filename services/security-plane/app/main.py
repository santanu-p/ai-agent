from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.engine import ingest_incident
from app.models import IncidentIngestRequest, RemediationResponse, SecurityIncident

app = FastAPI(title="AegisWorld Security Plane", version="0.1.0")
incidents: dict[str, SecurityIncident] = {}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "security-plane"}


@app.post("/v1/security/incidents/ingest", response_model=SecurityIncident)
def ingest(payload: IncidentIngestRequest) -> SecurityIncident:
    incident = ingest_incident(payload)
    incidents[incident.incident_id] = incident
    return incident


@app.get("/v1/security/incidents")
def list_incidents() -> dict[str, list[SecurityIncident]]:
    return {"incidents": list(incidents.values())}


@app.post("/v1/security/incidents/{incident_id}/remediate", response_model=RemediationResponse)
def remediate(incident_id: str) -> RemediationResponse:
    incident = incidents.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail={"error": "incident_not_found"})

    incident.verification_state = "completed"
    incidents[incident_id] = incident
    return RemediationResponse(
        incident_id=incident_id,
        actions_started=incident.auto_actions,
        status="completed",
    )

