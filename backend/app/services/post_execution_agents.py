import json
import os
import uuid
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models.audit_entry import AuditEntry
from app.models.incident import Incident
from app.services.session_containment_agent import run_session_containment
from app.services.threat_hunt_agent import run_threat_hunt


def _append_audit(db, incident_id: str, actor_name: str, event_name: str, target_system: str, details: dict):
    audit = AuditEntry(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        actor_type="ai_agent",
        actor_name=actor_name,
        event_name=event_name,
        target_system=target_system,
        details_json=json.dumps(details),
        timestamp=datetime.now(timezone.utc),
    )
    db.add(audit)
    db.commit()


def maybe_run_post_execution_agents(incident_id: str, operator_context: dict) -> list[dict]:
    """
    Run the new agentic layer only after the normal approved actions have executed.
    """
    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return []

        if incident.severity != "P1":
            return []

        incident_payload = {
            "id": incident.id,
            "title": incident.title,
            "summary": incident.summary,
            "severity": incident.severity,
            "slackEvidenceChannelId": os.getenv("WARROOM_SLACK_EVIDENCE_CHANNEL_ID"),
            "slackContainmentChannelId": os.getenv("WARROOM_SLACK_CONTAINMENT_CHANNEL_ID"),
        }

        hunt_result = run_threat_hunt(incident_payload, operator_context)
        _append_audit(
            db,
            incident.id,
            "Threat Hunt Agent",
            "Threat Hunt Agent completed evidence analysis",
            "Threat Analysis",
            hunt_result,
        )

        if not hunt_result.get("success"):
            return [hunt_result]

        containment_result = run_session_containment(
            incident_payload,
            operator_context,
            hunt_result,
            os.getenv("APP_BASE_URL", "http://localhost:8000"),
        )

        _append_audit(
            db,
            incident.id,
            "Session Containment Agent",
            "Session Containment Agent executed first-party controls",
            "Identity Control Plane",
            containment_result,
        )

        return [hunt_result, containment_result]
    finally:
        db.close()