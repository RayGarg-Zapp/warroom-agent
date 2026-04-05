import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class KnownIssueMatch(Base):
    __tablename__ = "known_issue_matches"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(50), ForeignKey("incidents.id"))
    known_issue_id = Column(String(50), ForeignKey("known_issues.id"))
    match_score = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    incident = relationship("Incident", back_populates="known_issue_matches")
    known_issue = relationship("KnownIssue")
