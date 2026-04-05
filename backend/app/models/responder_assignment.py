import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class ResponderAssignment(Base):
    __tablename__ = "responder_assignments"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(50), ForeignKey("incidents.id"))
    responder_id = Column(String(50), ForeignKey("responders.id"))
    confidence = Column(Float)
    assignment_role = Column(String(50))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    incident = relationship("Incident", back_populates="responder_assignments")
    responder = relationship("Responder")
