import uuid

from sqlalchemy import Column, String, Text

from app.database import Base


class KnownIssue(Base):
    __tablename__ = "known_issues"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    symptoms = Column(Text, nullable=True)
    keywords_json = Column(Text, nullable=True)
    domain = Column(String(50))
    remediation_steps = Column(Text)
    runbook_url = Column(String(500), nullable=True)
    severity_hint = Column(String(10), nullable=True)
    root_cause_summary = Column(Text, nullable=True)
    last_occurrence = Column(String(50), nullable=True)
