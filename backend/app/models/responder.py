import uuid

from sqlalchemy import Column, String, Boolean, Integer

from app.database import Base


class Responder(Base):
    __tablename__ = "responders"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False)
    slack_user_id = Column(String(100), nullable=True)
    team = Column(String(100), nullable=True)
    domain = Column(String(50), nullable=False)
    role = Column(String(200), nullable=True)
    timezone = Column(String(50), nullable=True)
    is_on_call = Column(Boolean, default=False)
    escalation_rank = Column(Integer, default=0)
    active = Column(Boolean, default=True)
