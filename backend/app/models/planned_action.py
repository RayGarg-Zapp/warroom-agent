import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class PlannedAction(Base):
    __tablename__ = "planned_actions"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(50), ForeignKey("incidents.id"))
    action_type = Column(String(50), nullable=False)
    title = Column(String(500))
    description = Column(Text, nullable=True)
    target_system = Column(String(100))
    payload_json = Column(Text, nullable=True)
    risk_level = Column(String(20), nullable=False)
    approval_required = Column(Boolean, default=True)
    approval_status = Column(String(20), default="pending")
    execution_status = Column(String(20), default="pending")
    provider = Column(String(100))
    scopes_used_json = Column(Text, nullable=True)
    recipients_json = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    executed_at = Column(DateTime, nullable=True)

    incident = relationship("Incident", back_populates="planned_actions")
    audit_entries = relationship("AuditEntry", back_populates="action")
