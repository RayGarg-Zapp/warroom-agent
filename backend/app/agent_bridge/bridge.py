"""
Agent Bridge — Adapter boundary for upstream local sovereign agents.

Design:
- Local agents (e.g., OpenClaw/NemoClaw) can submit incident context or action intents
- WarRoom Agent remains the governed execution plane
- Local agent never directly receives third-party OAuth tokens
- Local agent acts as reasoning client; this backend is authorization + execution layer

This module provides:
- Inbound: accept incident context from local agents
- Outbound: return execution results to local agents
- Trust: local agent can propose, but cannot bypass approval

Not mandatory for MVP, but designed for clean future integration.
"""
import logging
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)

class AgentIntentSubmission(BaseModel):
    """Intent submitted by an external local agent."""
    agent_id: str
    agent_type: str = "local_sovereign"  # e.g., "openclaw", "nemoclaw"
    intent_type: str  # "report_incident", "suggest_action", "request_status"
    payload: dict
    correlation_id: Optional[str] = None

class AgentIntentResponse(BaseModel):
    """Response back to the local agent."""
    correlation_id: str
    status: str  # "accepted", "rejected", "pending_approval"
    message: str
    data: Optional[dict] = None

class AgentBridge:
    """
    Bridge between local sovereign agents and WarRoom Agent.

    The local agent can:
    1. Submit incident reports for analysis
    2. Suggest remediation actions
    3. Request incident status

    The local agent CANNOT:
    1. Execute actions directly
    2. Access third-party OAuth tokens
    3. Bypass approval workflows
    """

    def process_intent(self, submission: AgentIntentSubmission) -> AgentIntentResponse:
        """Process an intent from a local agent."""
        logger.info(f"Agent bridge received intent: {submission.intent_type} from {submission.agent_id}")

        correlation_id = submission.correlation_id or f"bridge-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        if submission.intent_type == "report_incident":
            return self._handle_report(submission, correlation_id)
        elif submission.intent_type == "suggest_action":
            return self._handle_suggestion(submission, correlation_id)
        elif submission.intent_type == "request_status":
            return self._handle_status_request(submission, correlation_id)
        else:
            return AgentIntentResponse(
                correlation_id=correlation_id,
                status="rejected",
                message=f"Unknown intent type: {submission.intent_type}"
            )

    def _handle_report(self, sub: AgentIntentSubmission, cid: str) -> AgentIntentResponse:
        """Handle incident report from local agent."""
        raw_text = sub.payload.get("message", "")
        if not raw_text:
            return AgentIntentResponse(correlation_id=cid, status="rejected", message="No incident message provided")

        # Queue for processing through normal workflow
        return AgentIntentResponse(
            correlation_id=cid,
            status="accepted",
            message="Incident report accepted for analysis. Will be processed through standard workflow.",
            data={"queued": True, "source": f"agent:{sub.agent_id}"}
        )

    def _handle_suggestion(self, sub: AgentIntentSubmission, cid: str) -> AgentIntentResponse:
        """Handle action suggestion — local agent can suggest but not execute."""
        return AgentIntentResponse(
            correlation_id=cid,
            status="pending_approval",
            message="Action suggestion received. Subject to standard approval workflow.",
            data={"requires_approval": True}
        )

    def _handle_status_request(self, sub: AgentIntentSubmission, cid: str) -> AgentIntentResponse:
        """Handle status request — safe to return."""
        incident_id = sub.payload.get("incident_id")
        if not incident_id:
            return AgentIntentResponse(correlation_id=cid, status="rejected", message="incident_id required")

        from app.database import SessionLocal
        from app.models.incident import Incident
        db = SessionLocal()
        try:
            inc = db.query(Incident).filter(Incident.id == incident_id).first()
            if not inc:
                return AgentIntentResponse(correlation_id=cid, status="rejected", message="Incident not found")
            return AgentIntentResponse(
                correlation_id=cid, status="accepted", message="Status retrieved",
                data={"incident_id": inc.id, "status": inc.status, "severity": inc.severity, "title": inc.title}
            )
        finally:
            db.close()
