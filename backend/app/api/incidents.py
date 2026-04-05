from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_entry import AuditEntry
from app.models.incident import Incident
from app.models.known_issue import KnownIssue
from app.models.known_issue_match import KnownIssueMatch
from app.models.planned_action import PlannedAction
from app.models.responder import Responder
from app.models.responder_assignment import ResponderAssignment
from app.security.auth0_jwt import require_scopes

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

READ_INCIDENTS = "read:incidents"
ADMIN_CONFIG = "admin:config"


def _serialize_incident(inc: Incident, db: Session) -> dict:
    assignments = db.query(ResponderAssignment).filter(ResponderAssignment.incident_id == inc.id).all()
    responders = []
    for a in assignments:
        r = db.query(Responder).filter(Responder.id == a.responder_id).first()
        if r:
            responders.append(
                {
                    "id": r.id,
                    "name": r.name,
                    "role": r.role or "",
                    "domain": r.domain,
                    "email": r.email,
                    "avatar": None,
                    "available": r.is_on_call,
                    "confidence": a.confidence,
                }
            )

    ki_matches = db.query(KnownIssueMatch).filter(KnownIssueMatch.incident_id == inc.id).all()
    known_issues = []
    for m in ki_matches:
        ki = db.query(KnownIssue).filter(KnownIssue.id == m.known_issue_id).first()
        if ki:
            known_issues.append(
                {
                    "id": ki.id,
                    "title": ki.title,
                    "description": ki.symptoms or ki.root_cause_summary or "",
                    "matchScore": m.match_score,
                    "resolution": ki.remediation_steps or "",
                    "lastOccurrence": ki.last_occurrence or "",
                }
            )

    actions = db.query(PlannedAction).filter(PlannedAction.incident_id == inc.id).all()
    planned_actions = []
    for a in actions:
        planned_actions.append(
            {
                "id": a.id,
                "incidentId": a.incident_id,
                "type": a.action_type,
                "title": a.title or "",
                "description": a.description or "",
                "riskLevel": a.risk_level,
                "status": a.approval_status,
                "executionStatus": a.execution_status,
                "provider": a.provider or "",
                "scopesUsed": json.loads(a.scopes_used_json) if a.scopes_used_json else [],
                "recipients": json.loads(a.recipients_json) if a.recipients_json else [],
                "metadata": json.loads(a.metadata_json) if a.metadata_json else {},
                "createdAt": a.created_at.isoformat() + "Z" if a.created_at else "",
                "executedAt": (a.executed_at.isoformat() + "Z") if a.executed_at else None,
            }
        )

    audits = db.query(AuditEntry).filter(AuditEntry.incident_id == inc.id).order_by(AuditEntry.timestamp).all()
    audit_entries = []
    for ae in audits:
        audit_entries.append(
            {
                "id": ae.id,
                "incidentId": ae.incident_id,
                "event": ae.event_name,
                "timestamp": ae.timestamp.isoformat() + "Z" if ae.timestamp else "",
                "actorType": ae.actor_type,
                "actorName": ae.actor_name,
                "targetSystem": ae.target_system or "",
                "approvalStatus": ae.approval_status,
                "executionStatus": ae.execution_status,
                "metadata": json.loads(ae.details_json) if ae.details_json else None,
            }
        )

    domains = json.loads(inc.probable_domains_json) if inc.probable_domains_json else []
    impacted = json.loads(inc.impacted_systems_json) if inc.impacted_systems_json else []

    return {
        "id": inc.id,
        "title": inc.title,
        "severity": inc.severity,
        "status": inc.status,
        "source": inc.source,
        "slackMessage": inc.raw_text,
        "aiSummary": inc.summary or "",
        "severityReasoning": inc.severity_reasoning or "",
        "confidenceScore": inc.confidence or 0.0,
        "impactedSystems": impacted,
        "domains": domains,
        "responders": responders,
        "knownIssues": known_issues,
        "plannedActions": planned_actions,
        "auditEntries": audit_entries,
        "detectedAt": inc.created_at.isoformat() + "Z" if inc.created_at else "",
        "updatedAt": inc.updated_at.isoformat() + "Z" if inc.updated_at else "",
    }


@router.get("")
def list_incidents(
    severity: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_scopes(READ_INCIDENTS)),
):
    query = db.query(Incident).order_by(Incident.created_at.desc())

    if severity:
        query = query.filter(Incident.severity == severity)
    if status:
        query = query.filter(Incident.status == status)
    if search:
        query = query.filter(or_(Incident.title.contains(search), Incident.raw_text.contains(search)))

    incidents = query.all()
    return {
        "data": [_serialize_incident(i, db) for i in incidents],
        "error": None,
        "meta": {
            "total": len(incidents),
            "viewer": current_user.get("email") or current_user.get("sub"),
        },
    }


@router.get("/{incident_id}")
def get_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_scopes(READ_INCIDENTS)),
):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    return {
        "data": _serialize_incident(inc, db),
        "error": None,
        "meta": {"viewer": current_user.get("email") or current_user.get("sub")},
    }


@router.post("/inject")
def inject_incident(
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_scopes(ADMIN_CONFIG)),
):
    raw_text = body.get("slackMessage", body.get("raw_text", ""))
    source = body.get("source", "#incidents-prod")
    if not raw_text:
        raise HTTPException(status_code=400, detail="slackMessage is required")

    from app.agents.workflow import incident_workflow

    incident_id = body.get("id", f"INC-{datetime.now().strftime('%Y')}-{str(uuid.uuid4())[:3].upper()}")

    initial_state = {
        "incident_id": incident_id,
        "raw_message": raw_text,
        "source": source,
        "slack_channel_id": None,
        "slack_message_ts": None,
        "severity": None,
        "confidence": None,
        "title": None,
        "summary": None,
        "severity_reasoning": None,
        "probable_domains": None,
        "impacted_systems": None,
        "responders": None,
        "known_issues": None,
        "proposed_actions": None,
        "approvals_required": None,
        "all_approved": None,
        "execution_results": None,
        "audit_entries": [],
        "current_stage": "ingesting",
        "errors": None,
    }

    result = incident_workflow.invoke(initial_state)

    incident = Incident(
        id=incident_id,
        source=source,
        raw_text=raw_text,
        title=result.get("title") or "Untitled Incident",
        severity=result.get("severity") or "P2",
        confidence=result.get("confidence") or 0.0,
        summary=result.get("summary") or "",
        severity_reasoning=result.get("severity_reasoning") or "",
        probable_domains_json=json.dumps(result.get("probable_domains") or []),
        impacted_systems_json=json.dumps(result.get("impacted_systems") or []),
        status=result.get("current_stage", "awaiting_approval") if result.get("approvals_required") else "in_progress",
    )
    db.add(incident)
    db.flush()

    for r_data in (result.get("responders") or []):
        db.add(
            ResponderAssignment(
                id=str(uuid.uuid4()),
                incident_id=incident_id,
                responder_id=r_data["id"],
                confidence=r_data.get("confidence", 0.0),
                assignment_role="primary",
            )
        )

    for ki_data in (result.get("known_issues") or []):
        db.add(
            KnownIssueMatch(
                id=str(uuid.uuid4()),
                incident_id=incident_id,
                known_issue_id=ki_data["id"],
                match_score=ki_data.get("matchScore", 0.0),
            )
        )

    for a_data in (result.get("proposed_actions") or []):
        db.add(
            PlannedAction(
                id=str(uuid.uuid4()),
                incident_id=incident_id,
                action_type=a_data.get("action_type", ""),
                title=a_data.get("title", ""),
                description=a_data.get("description", ""),
                target_system=a_data.get("provider", ""),
                risk_level=a_data.get("risk_level", "medium"),
                approval_required=a_data.get("risk_level", "medium") in ("high", "critical"),
                approval_status="pending",
                execution_status="pending",
                provider=a_data.get("provider", ""),
                scopes_used_json=json.dumps(a_data.get("scopes_used", [])),
                recipients_json=json.dumps(a_data.get("recipients", [])),
                metadata_json=json.dumps(a_data.get("metadata", {})),
            )
        )

    for ae_data in (result.get("audit_entries") or []):
        db.add(
            AuditEntry(
                id=str(uuid.uuid4()),
                incident_id=incident_id,
                actor_type=ae_data.get("actor_type", "system"),
                actor_name=ae_data.get("actor_name", "WarRoom Agent"),
                event_name=ae_data.get("event", ""),
                target_system=ae_data.get("target_system", ""),
                details_json=ae_data.get("details_json"),
                timestamp=datetime.fromisoformat(ae_data["timestamp"].replace("Z", "+00:00"))
                if ae_data.get("timestamp")
                else datetime.now(timezone.utc),
            )
        )

    db.add(
        AuditEntry(
            id=str(uuid.uuid4()),
            incident_id=incident_id,
            actor_type="human",
            actor_id=current_user.get("sub"),
            actor_name=current_user.get("name") or current_user.get("email") or "Operator",
            event_name=f"Demo incident injected: {incident.title}",
            target_system=source,
            details_json=json.dumps(
                {
                    "requestedByEmail": current_user.get("email"),
                    "requestedBySub": current_user.get("sub"),
                }
            ),
            timestamp=datetime.now(timezone.utc),
        )
    )

    db.commit()
    db.refresh(incident)

    # Grant default approvers in FGA
    try:
        from app.security.fga_client import fga_client
        fga_client.grant_incident_approvers(incident_id)
    except Exception as fga_err:
        import logging
        logging.getLogger(__name__).warning("[FGA] Failed to grant approvers for %s: %s", incident_id, fga_err)

    return {"data": _serialize_incident(incident, db), "error": None, "meta": {}}
