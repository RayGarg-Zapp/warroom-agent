import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_entry import AuditEntry
from app.models.incident import Incident
from app.models.integration_connection import IntegrationConnection
from app.models.known_issue import KnownIssue
from app.models.known_issue_match import KnownIssueMatch
from app.models.planned_action import PlannedAction
from app.models.responder import Responder
from app.models.responder_assignment import ResponderAssignment
from app.security.auth0_jwt import require_scopes

router = APIRouter(prefix="/api/demo", tags=["demo"])
logger = logging.getLogger(__name__)

ADMIN_CONFIG = "admin:config"

SEED_RESPONDERS = [
    {"id": "resp-1", "name": "Priya Sharma", "email": "priya@acme.io", "domain": "backend",
     "role": "Senior SRE", "team": "Platform", "is_on_call": True, "escalation_rank": 1},
    {"id": "resp-2", "name": "Alex Chen", "email": "alex@acme.io", "domain": "infrastructure",
     "role": "Staff Infrastructure Engineer", "team": "Infra", "is_on_call": True, "escalation_rank": 2},
    {"id": "resp-3", "name": "Jordan Lee", "email": "jordan@acme.io", "domain": "database",
     "role": "DBA Lead", "team": "Data Platform", "is_on_call": False, "escalation_rank": 3},
    {"id": "resp-4", "name": "Sam Rivera", "email": "sam@acme.io", "domain": "frontend",
     "role": "Frontend Lead", "team": "Web", "is_on_call": False, "escalation_rank": 4},
]

SEED_KNOWN_ISSUES = [
    {
        "id": "ki-1",
        "title": "Connection pool exhaustion under high load",
        "description": "PostgreSQL connection pool saturates when request rate exceeds 5k rps",
        "symptoms": "5xx errors spike, pg_stat_activity shows all connections in use, response latency > 30s",
        "domain": "backend",
        "severity_hint": "P1",
        "remediation_steps": "1. Scale up read replicas\n2. Increase pool max from 20 to 50\n3. Enable PgBouncer",
        "root_cause_summary": "Default pool size too small for peak traffic",
        "last_occurrence": "2026-02-15",
        "keywords_json": json.dumps(["connection pool", "postgres", "5xx", "timeout"]),
    },
    {
        "id": "ki-2",
        "title": "Redis cache stampede during deploy",
        "description": "Cache invalidation during rolling deploy causes thundering herd",
        "symptoms": "CPU spikes on Redis nodes, cache hit rate drops to 0%, API latency 10x",
        "domain": "infrastructure",
        "severity_hint": "P2",
        "remediation_steps": "1. Enable stale-while-revalidate\n2. Stagger cache TTLs\n3. Use deployment lock",
        "root_cause_summary": "All cache keys expire simultaneously after deploy",
        "last_occurrence": "2026-01-20",
        "keywords_json": json.dumps(["redis", "cache", "deploy", "stampede", "latency"]),
    },
]

SEED_INTEGRATIONS = [
    {"id": "int-slack", "provider_name": "Slack", "icon": "slack",
     "connection_status": "connected",
     "scopes_json": json.dumps(["chat:write", "channels:read", "users:read"]),
     "security_note": "OAuth2 bot token — minimal scopes"},
    {"id": "int-zoom", "provider_name": "Zoom", "icon": "video",
     "connection_status": "connected",
     "scopes_json": json.dumps(["meeting:write", "user:read"]),
     "security_note": "Server-to-server OAuth — no user consent required"},
    {"id": "int-gcal", "provider_name": "Google Calendar", "icon": "calendar",
     "connection_status": "connected",
     "scopes_json": json.dumps(["calendar.events"]),
     "security_note": "Service account — domain-wide delegation"},
    {"id": "int-email", "provider_name": "Email (SMTP)", "icon": "mail",
     "connection_status": "connected",
     "scopes_json": json.dumps(["send"]),
     "security_note": "SMTP relay via internal gateway"},
]

SAMPLE_INCIDENT_ID = "INC-2026-001"


def _seed_sample_incident(db: Session):
    now = datetime.now(timezone.utc)

    incident = Incident(
        id=SAMPLE_INCIDENT_ID,
        source="#incidents-prod",
        raw_text="@incident-bot URGENT: API gateway returning 503 for all /v2/payments endpoints. Error rate spiked from 0.1% to 45% in the last 5 minutes. Multiple customers reporting failed transactions. Grafana alert firing.",
        title="Payment API Gateway 503 — 45% Error Rate Spike",
        severity="P1",
        confidence=0.94,
        summary="Critical outage affecting the /v2/payments endpoints via the API gateway. Error rate jumped from baseline 0.1% to 45% within 5 minutes, causing widespread customer-facing transaction failures.",
        severity_reasoning="P1: Customer-impacting outage on a revenue-critical path (payments). 45% error rate indicates a major service degradation, not a partial issue.",
        probable_domains_json=json.dumps(["backend", "infrastructure"]),
        impacted_systems_json=json.dumps(["api-gateway", "payments-service", "postgres-primary"]),
        status="awaiting_approval",
        created_at=now,
        updated_at=now,
    )
    db.merge(incident)

    for rid, conf in [("resp-1", 0.95), ("resp-2", 0.88)]:
        db.merge(
            ResponderAssignment(
                id=f"ra-{rid}",
                incident_id=SAMPLE_INCIDENT_ID,
                responder_id=rid,
                confidence=conf,
                assignment_role="primary",
                created_at=now,
            )
        )

    db.merge(
        KnownIssueMatch(
            id="kim-1",
            incident_id=SAMPLE_INCIDENT_ID,
            known_issue_id="ki-1",
            match_score=0.87,
            created_at=now,
        )
    )

    actions_data = [
        {
            "id": "act-1",
            "action_type": "zoom_meeting",
            "title": "Create War Room Bridge",
            "description": "Spin up a Zoom meeting and invite the on-call responders",
            "risk_level": "low",
            "provider": "Zoom",
            "scopes_used": ["meeting:write"],
            "recipients": ["priya@acme.io", "alex@acme.io"],
        },
        {
            "id": "act-2",
            "action_type": "slack_dm",
            "title": "Page On-Call Responders",
            "description": "Send Slack DMs to Priya Sharma and Alex Chen with incident details",
            "risk_level": "low",
            "provider": "Slack",
            "scopes_used": ["chat:write"],
            "recipients": ["priya@acme.io", "alex@acme.io"],
        },
        {
            "id": "act-3",
            "action_type": "calendar_event",
            "title": "Block Responder Calendars",
            "description": "Create a 1-hour calendar hold for the incident war room",
            "risk_level": "medium",
            "provider": "Google Calendar",
            "scopes_used": ["calendar.events"],
            "recipients": ["priya@acme.io", "alex@acme.io"],
        },
        {
            "id": "act-4",
            "action_type": "email_notification",
            "title": "Notify VP Engineering & Stakeholders",
            "description": "Send email summary to leadership and stakeholder distribution list",
            "risk_level": "high",
            "provider": "Email (SMTP)",
            "scopes_used": ["send"],
            "recipients": ["vp-eng@acme.io", "incident-stakeholders@acme.io"],
        },
    ]

    for ad in actions_data:
        db.merge(
            PlannedAction(
                id=ad["id"],
                incident_id=SAMPLE_INCIDENT_ID,
                action_type=ad["action_type"],
                title=ad["title"],
                description=ad["description"],
                target_system=ad["provider"],
                risk_level=ad["risk_level"],
                approval_required=ad["risk_level"] in ("high", "critical"),
                approval_status="pending",
                execution_status="pending",
                provider=ad["provider"],
                scopes_used_json=json.dumps(ad["scopes_used"]),
                recipients_json=json.dumps(ad["recipients"]),
                metadata_json=json.dumps({}),
                created_at=now,
            )
        )

    audit_events = [
        {"event": "Incident ingested from Slack", "actor_type": "system", "actor_name": "Slack Ingest"},
        {"event": "Classified as P1 (confidence 0.94)", "actor_type": "ai", "actor_name": "GPT-4o Classifier"},
        {"event": "Matched known issue: Connection pool exhaustion (87%)", "actor_type": "ai", "actor_name": "Known Issue Engine"},
        {"event": "Responders resolved: Priya Sharma, Alex Chen", "actor_type": "ai", "actor_name": "Responder Resolver"},
        {"event": "4 actions planned — awaiting human approval", "actor_type": "ai", "actor_name": "Action Planner"},
    ]

    for i, ae in enumerate(audit_events):
        db.merge(
            AuditEntry(
                id=f"ae-{i+1}",
                incident_id=SAMPLE_INCIDENT_ID,
                actor_type=ae["actor_type"],
                actor_name=ae["actor_name"],
                event_name=ae["event"],
                timestamp=now,
            )
        )

    db.commit()


@router.post("/seed")
def seed_demo_data(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_scopes(ADMIN_CONFIG)),
):
    for r in SEED_RESPONDERS:
        db.merge(Responder(**r))

    for ki in SEED_KNOWN_ISSUES:
        db.merge(KnownIssue(**ki))

    for ic in SEED_INTEGRATIONS:
        db.merge(IntegrationConnection(**ic))

    db.commit()
    _seed_sample_incident(db)

    db.add(
        AuditEntry(
            id=str(datetime.now(timezone.utc).timestamp()).replace(".", ""),
            actor_type="human",
            actor_id=current_user.get("sub"),
            actor_name=current_user.get("name") or current_user.get("email") or "Operator",
            event_name="Demo data seeded",
            target_system="Seed Engine",
            details_json=json.dumps(
                {
                    "seededByEmail": current_user.get("email"),
                    "seededBySub": current_user.get("sub"),
                }
            ),
            timestamp=datetime.now(timezone.utc),
        )
    )
    db.commit()

    logger.info("Demo data seeded successfully")
    return {
        "data": {
            "seeded": True,
            "responders": len(SEED_RESPONDERS),
            "knownIssues": len(SEED_KNOWN_ISSUES),
            "integrations": len(SEED_INTEGRATIONS),
            "sampleIncidentId": SAMPLE_INCIDENT_ID,
        },
        "error": None,
        "meta": {},
    }


@router.get("/health")
def health_check():
    return {
        "data": {"status": "healthy", "service": "warroom-agent", "version": "1.0.0"},
        "error": None,
        "meta": {},
    }