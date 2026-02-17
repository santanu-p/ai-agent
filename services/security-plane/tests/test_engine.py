from __future__ import annotations

from app.engine import classify_severity, ingest_incident, remediation_plan
from app.models import IncidentIngestRequest, Severity


def test_classify_severity_critical() -> None:
    severity = classify_severity(["privilege_escalation detected"])
    assert severity == Severity.critical


def test_remediation_plan_high() -> None:
    actions = remediation_plan(Severity.high)
    assert "rotate-credentials" in actions
    assert "quarantine-workload" in actions


def test_ingest_incident_creates_actions() -> None:
    incident = ingest_incident(
        IncidentIngestRequest(
            signal_set=["guardduty anomalous-api-call", "waf burst"],
            source="guardduty",
        )
    )
    assert incident.incident_id
    assert incident.auto_actions

