from __future__ import annotations

import logging
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models.audit_entry import AuditEntry
import uuid

logger = logging.getLogger(__name__)

def log_audit_event(
    event_name: str,
    actor_type: str = "system",
    actor_name: str = "WarRoom Agent",
    incident_id: str | None = None,
    action_id: str | None = None,
    target_system: str = "",
    details: dict | None = None,
    approval_status: str | None = None,
    execution_status: str | None = None,
) -> AuditEntry:
    """Append a structured audit entry."""
    import json
    db = SessionLocal()
    try:
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            incident_id=incident_id,
            action_id=action_id,
            actor_type=actor_type,
            actor_id=None,
            actor_name=actor_name,
            event_name=event_name,
            target_system=target_system,
            details_json=json.dumps(details) if details else None,
            approval_status=approval_status,
            execution_status=execution_status,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    finally:
        db.close()

def get_audit_entries(incident_id: str | None = None, search: str | None = None,
                      actor_type: str | None = None, limit: int = 100) -> list[AuditEntry]:
    db = SessionLocal()
    try:
        query = db.query(AuditEntry).order_by(AuditEntry.timestamp.desc())
        if incident_id:
            query = query.filter(AuditEntry.incident_id == incident_id)
        if actor_type:
            query = query.filter(AuditEntry.actor_type == actor_type)
        if search:
            query = query.filter(AuditEntry.event_name.contains(search))
        return query.limit(limit).all()
    finally:
        db.close()
