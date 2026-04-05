from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ResponderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    name: str
    role: str = ""
    domain: str = ""
    email: str = ""
    avatar: Optional[str] = None
    available: bool = Field(alias="available", default=True)
    confidence: float = Field(alias="confidence", default=0.0)
