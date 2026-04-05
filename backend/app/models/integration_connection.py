import uuid

from sqlalchemy import Column, String, Text, DateTime

from app.database import Base


class IntegrationConnection(Base):
    __tablename__ = "integration_connections"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), nullable=True)
    provider_name = Column(String(100), nullable=False)
    icon = Column(String(50), nullable=True)
    connection_status = Column(String(20), default="disconnected")
    scopes_json = Column(Text, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    security_note = Column(Text, nullable=True)
    auth0_reference_id = Column(String(200), nullable=True)
