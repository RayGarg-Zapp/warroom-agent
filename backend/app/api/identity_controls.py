import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_entry import AuditEntry
from app.security.auth0_jwt import require_scopes

router = APIRouter(prefix="/api/identity", tags=["identity-controls"])


@router.post("/revoke-sessions")
def revoke_sessions(
    body: dict,
    db: Session = Depends(get_db),
    current_agent: dict = Depends(require_scopes("identity:revoke_sessions")),
):
    incident_id = body.get("incident_id")
    target_user_id = body.get("target_user_id")

    if not incident_id or not target_user_id:
        raise HTTPException(status_code=400, detail="incident_id and target_user_id are required")

    audit = AuditEntry(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        actor_type="ai_agent",
        actor_id=current_agent.get("azp") or current_agent.get("sub"),
        actor_name="Session Containment Agent",
        event_name="Identity control executed: revoke sessions",
        target_system="Session Service",
        execution_status="executed",
        details_json=json.dumps(
            {
                "target_user_id": target_user_id,
                "scope": current_agent.get("scope"),
                "client_id": current_agent.get("azp"),
            }
        ),
        timestamp=datetime.now(timezone.utc),
    )
    db.add(audit)
    db.commit()

    return {
        "data": {
            "success": True,
            "action": "revoke_sessions",
            "target_user_id": target_user_id,
            "status": "revoked",
        },
        "error": None,
        "meta": {},
    }


@router.post("/disable-client")
def disable_client(
    body: dict,
    db: Session = Depends(get_db),
    current_agent: dict = Depends(require_scopes("identity:disable_client")),
):
    incident_id = body.get("incident_id")
    target_client_id = body.get("target_client_id")

    if not incident_id or not target_client_id:
        raise HTTPException(status_code=400, detail="incident_id and target_client_id are required")

    audit = AuditEntry(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        actor_type="ai_agent",
        actor_id=current_agent.get("azp") or current_agent.get("sub"),
        actor_name="Session Containment Agent",
        event_name="Identity control executed: disable client",
        target_system="Admin Console",
        execution_status="executed",
        details_json=json.dumps(
            {
                "target_client_id": target_client_id,
                "scope": current_agent.get("scope"),
                "client_id": current_agent.get("azp"),
            }
        ),
        timestamp=datetime.now(timezone.utc),
    )
    db.add(audit)
    db.commit()

    return {
        "data": {
            "success": True,
            "action": "disable_client",
            "target_client_id": target_client_id,
            "status": "disabled",
        },
        "error": None,
        "meta": {},
    }