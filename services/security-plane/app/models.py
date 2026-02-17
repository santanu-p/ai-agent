from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class BlastRadius(str, Enum):
    host = "host"
    service = "service"
    region = "region"
    global_scope = "global"


class IncidentIngestRequest(BaseModel):
    signal_set: list[str] = Field(default_factory=list)
    source: str
    metadata: dict[str, str] = Field(default_factory=dict)


class SecurityIncident(BaseModel):
    incident_id: str
    signal_set: list[str]
    severity: Severity
    blast_radius: BlastRadius
    auto_actions: list[str]
    verification_state: str


class RemediationResponse(BaseModel):
    incident_id: str
    actions_started: list[str]
    status: str

