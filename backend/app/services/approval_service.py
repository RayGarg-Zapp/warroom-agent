from __future__ import annotations

import logging
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models.planned_action import PlannedAction
from app.models.audit_entry import AuditEntry
import uuid

logger = logging.getLogger(__name__)

def get_pending_actions(incident_id: str | None = None) -> list[PlannedAction]:
    db = SessionLocal()
    try:
        query = db.query(PlannedAction).filter(PlannedAction.approval_status == "pending")
        if incident_id:
            query = query.filter(PlannedAction.incident_id == incident_id)
        return query.all()
    finally:
        db.close()

def approve_action(action_id: str, actor_name: str = "operator") -> PlannedAction | None:
    db = SessionLocal()
    try:
        action = db.query(PlannedAction).filter(PlannedAction.id == action_id).first()
        if not action:
            return None
        action.approval_status = "approved"

        audit = AuditEntry(
            id=str(uuid.uuid4()),
            incident_id=action.incident_id,
            action_id=action.id,
            actor_type="human",
            actor_id=actor_name,
            actor_name=actor_name,
            event_name=f"Action approved: {action.title}",
            target_system=action.provider or action.target_system,
            approval_status="approved",
            timestamp=datetime.now(timezone.utc),
        )
        db.add(audit)
        db.commit()
        db.refresh(action)
        return action
    finally:
        db.close()

def deny_action(action_id: str, actor_name: str = "operator") -> PlannedAction | None:
    db = SessionLocal()
    try:
        action = db.query(PlannedAction).filter(PlannedAction.id == action_id).first()
        if not action:
            return None
        action.approval_status = "denied"
        action.execution_status = "failed"

        audit = AuditEntry(
            id=str(uuid.uuid4()),
            incident_id=action.incident_id,
            action_id=action.id,
            actor_type="human",
            actor_id=actor_name,
            actor_name=actor_name,
            event_name=f"Action denied: {action.title}",
            target_system=action.provider or action.target_system,
            approval_status="denied",
            timestamp=datetime.now(timezone.utc),
        )
        db.add(audit)
        db.commit()
        db.refresh(action)
        return action
    finally:
        db.close()

def check_all_approved(incident_id: str) -> bool:
    """Check if all actions requiring approval have been approved."""
    db = SessionLocal()
    try:
        pending = db.query(PlannedAction).filter(
            PlannedAction.incident_id == incident_id,
            PlannedAction.approval_required == True,
            PlannedAction.approval_status == "pending"
        ).count()
        return pending == 0
    finally:
        db.close()
