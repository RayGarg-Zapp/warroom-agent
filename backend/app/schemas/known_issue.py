from pydantic import BaseModel, ConfigDict, Field


class KnownIssueMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    title: str = ""
    description: str = ""
    match_score: float = Field(alias="matchScore", default=0.0)
    resolution: str = ""
    last_occurrence: str = Field(alias="lastOccurrence", default="")
