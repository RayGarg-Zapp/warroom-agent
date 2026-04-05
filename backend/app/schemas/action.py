from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PlannedActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    incident_id: str = Field(alias="incidentId", default="")
    type: str = ""
    title: str = ""
    description: str = ""
    risk_level: str = Field(alias="riskLevel", default="low")
    status: str = "pending"
    provider: str = ""
    scopes_used: list[str] = Field(alias="scopesUsed", default_factory=list)
    recipients: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(alias="createdAt", default="")
    executed_at: Optional[str] = Field(alias="executedAt", default=None)
