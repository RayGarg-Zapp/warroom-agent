from pydantic import BaseModel, ConfigDict, Field


class IntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    provider: str = ""
    icon: str = ""
    status: str = "disconnected"
    scopes_granted: list[str] = Field(alias="scopesGranted", default_factory=list)
    last_used: str = Field(alias="lastUsed", default="")
    security_note: str = Field(alias="securityNote", default="")
