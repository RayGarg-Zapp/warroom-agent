import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(50), ForeignKey("incidents.id"), nullable=True)
    action_id = Column(String(50), ForeignKey("planned_actions.id"), nullable=True)
    actor_type = Column(String(30))
    actor_id = Column(String(100), nullable=True)
    actor_name = Column(String(200))
    event_name = Column(String(200), nullable=False)
    target_system = Column(String(100), nullable=True)
    details_json = Column(Text, nullable=True)
    approval_status = Column(String(20), nullable=True)
    execution_status = Column(String(20), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    incident = relationship("Incident", back_populates="audit_entries")
    action = relationship("PlannedAction", back_populates="audit_entries")
