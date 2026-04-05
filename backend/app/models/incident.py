import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Float, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String(100))
    slack_channel_id = Column(String(100), nullable=True)
    slack_message_ts = Column(String(50), nullable=True)
    raw_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=True)
    title = Column(String(500), nullable=False)
    severity = Column(String(10), nullable=False)
    confidence = Column(Float, default=0.0)
    summary = Column(Text, nullable=True)
    severity_reasoning = Column(Text, nullable=True)
    probable_domains_json = Column(Text, nullable=True)
    impacted_systems_json = Column(Text, nullable=True)
    status = Column(String(30), default="detected")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    responder_assignments = relationship(
        "ResponderAssignment", back_populates="incident"
    )
    known_issue_matches = relationship("KnownIssueMatch", back_populates="incident")
    planned_actions = relationship("PlannedAction", back_populates="incident")
    audit_entries = relationship("AuditEntry", back_populates="incident")
