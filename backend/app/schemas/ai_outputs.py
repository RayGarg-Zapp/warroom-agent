from pydantic import BaseModel, Field


class IncidentClassificationOutput(BaseModel):
    """Structured output from LLM incident classification."""

    severity: str = "P3"
    confidence: float = 0.0
    title: str = ""
    summary: str = ""
    severity_reasoning: str = ""
    probable_domains: list[str] = Field(default_factory=list)
    impacted_systems: list[str] = Field(default_factory=list)


class ResponderCandidate(BaseModel):
    """Single responder recommendation from the LLM."""

    responder_id: str
    confidence: float = 0.0
    role: str = ""


class ResponderSelectionOutput(BaseModel):
    """Structured output from LLM responder selection."""

    responders: list[ResponderCandidate] = Field(default_factory=list)


class KnownIssueCandidate(BaseModel):
    """Single known-issue match from the LLM."""

    known_issue_id: str
    match_score: float = 0.0
    explanation: str = ""


class KnownIssueMatchOutput(BaseModel):
    """Structured output from LLM known-issue matching."""

    matches: list[KnownIssueCandidate] = Field(default_factory=list)


class CommunicationAction(BaseModel):
    """Single communication action recommended by the LLM."""

    action_type: str = ""
    title: str = ""
    description: str = ""
    risk_level: str = "low"
    provider: str = ""
    recipients: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class CommunicationDraftOutput(BaseModel):
    """Structured output from LLM communication drafting."""

    actions: list[CommunicationAction] = Field(default_factory=list)
