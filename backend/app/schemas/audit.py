from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AuditEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    incident_id: str = Field(alias="incidentId", default="")
    event: str = ""
    timestamp: str = ""
    actor_type: str = Field(alias="actorType", default="system")
    actor_name: str = Field(alias="actorName", default="")
    target_system: str = Field(alias="targetSystem", default="")
    approval_status: Optional[str] = Field(alias="approvalStatus", default=None)
    execution_status: Optional[str] = Field(alias="executionStatus", default=None)
    metadata: Optional[dict[str, str]] = Field(default=None)
