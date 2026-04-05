from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_entry import AuditEntry
from app.security.auth0_jwt import require_scopes

router = APIRouter(prefix="/api/audit", tags=["audit"])

READ_AUDIT = "read:audit"


def _serialize_audit(ae: AuditEntry) -> dict:
    return {
        "id": ae.id,
        "incidentId": ae.incident_id,
        "actionId": ae.action_id,
        "event": ae.event_name,
        "timestamp": ae.timestamp.isoformat() + "Z" if ae.timestamp else "",
        "actorType": ae.actor_type,
        "actorName": ae.actor_name,
        "targetSystem": ae.target_system or "",
        "approvalStatus": ae.approval_status,
        "executionStatus": ae.execution_status,
        "metadata": json.loads(ae.details_json) if ae.details_json else None,
    }


@router.get("")
def list_audit_entries(
    incident_id: str | None = Query(None),
    search: str | None = Query(None),
    actor_type: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_scopes(READ_AUDIT)),
):
    query = db.query(AuditEntry).order_by(AuditEntry.timestamp.desc())

    if incident_id:
        query = query.filter(AuditEntry.incident_id == incident_id)
    if actor_type:
        query = query.filter(AuditEntry.actor_type == actor_type)
    if search:
        query = query.filter(
            or_(
                AuditEntry.event_name.contains(search),
                AuditEntry.actor_name.contains(search),
                AuditEntry.target_system.contains(search),
            )
        )

    entries = query.all()
    return {
        "data": [_serialize_audit(ae) for ae in entries],
        "error": None,
        "meta": {
            "total": len(entries),
            "viewer": current_user.get("email") or current_user.get("sub"),
        },
    }