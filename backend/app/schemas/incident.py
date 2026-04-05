from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.action import PlannedActionResponse
from app.schemas.audit import AuditEntryResponse
from app.schemas.known_issue import KnownIssueMatchResponse
from app.schemas.responder import ResponderResponse


class IncidentBase(BaseModel):
    title: str
    severity: str
    source: str = ""


class IncidentCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    raw_text: str = Field(alias="slackMessage")
    source: str = "#incidents-prod"
    slack_channel_id: Optional[str] = None


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    title: str
    severity: str
    status: str
    source: str
    slack_message: str = Field(alias="slackMessage", default="")
    ai_summary: str = Field(alias="aiSummary", default="")
    severity_reasoning: str = Field(alias="severityReasoning", default="")
    confidence_score: float = Field(alias="confidenceScore", default=0.0)
    impacted_systems: list[str] = Field(alias="impactedSystems", default_factory=list)
    domains: list[str] = Field(default_factory=list)
    responders: list[ResponderResponse] = Field(default_factory=list)
    known_issues: list[KnownIssueMatchResponse] = Field(
        alias="knownIssues", default_factory=list
    )
    planned_actions: list[PlannedActionResponse] = Field(
        alias="plannedActions", default_factory=list
    )
    audit_entries: list[AuditEntryResponse] = Field(
        alias="auditEntries", default_factory=list
    )
    detected_at: str = Field(alias="detectedAt", default="")
    updated_at: str = Field(alias="updatedAt", default="")
