from __future__ import annotations

from uuid import uuid4

from app.models import BlastRadius, IncidentIngestRequest, SecurityIncident, Severity


def classify_severity(signals: list[str]) -> Severity:
    joined = " ".join(signals).lower()
    if "credential" in joined or "privilege_escalation" in joined:
        return Severity.critical
    if "anomalous" in joined or "exfiltration" in joined:
        return Severity.high
    if "waf" in joined or "burst" in joined:
        return Severity.medium
    return Severity.low


def estimate_blast_radius(severity: Severity, signals: list[str]) -> BlastRadius:
    joined = " ".join(signals).lower()
    if severity == Severity.critical:
        return BlastRadius.global_scope
    if "region" in joined:
        return BlastRadius.region
    if severity == Severity.high:
        return BlastRadius.service
    return BlastRadius.host


def remediation_plan(severity: Severity) -> list[str]:
    if severity == Severity.critical:
        return [
            "rotate-credentials",
            "quarantine-workload",
            "tighten-network-policy",
            "redeploy-hardened-image",
            "invalidate-sessions",
        ]
    if severity == Severity.high:
        return [
            "rotate-credentials",
            "quarantine-workload",
            "tighten-network-policy",
        ]
    if severity == Severity.medium:
        return ["rate-limit-source", "tighten-waf-rule"]
    return ["monitor-and-log"]


def ingest_incident(request: IncidentIngestRequest) -> SecurityIncident:
    severity = classify_severity(request.signal_set)
    radius = estimate_blast_radius(severity, request.signal_set)
    actions = remediation_plan(severity)
    return SecurityIncident(
        incident_id=str(uuid4()),
        signal_set=request.signal_set,
        severity=severity,
        blast_radius=radius,
        auto_actions=actions,
        verification_state="in_progress",
    )

