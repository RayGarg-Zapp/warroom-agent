from __future__ import annotations

"""
WarRoom Agent — AI Chat endpoint for incident remediation assistance.

Provides a conversational interface where operators can discuss fixes,
get code/config suggestions, and push remediation actions — all scoped
to a specific incident's context.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import anthropic
from app.config import get_settings
from app.database import get_db
from app.models.incident import Incident
from app.models.planned_action import PlannedAction
from app.models.known_issue_match import KnownIssueMatch
from app.models.known_issue import KnownIssue
from app.models.audit_entry import AuditEntry
from app.security.auth0_jwt import require_scopes

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)

READ_INCIDENTS = "read:incidents"

SYSTEM_PROMPT = """\
You are WarRoom Agent, an expert AI incident-response assistant embedded in an \
enterprise incident coordination console. You are chatting with an on-call \
operator who is actively handling a live incident.

### Your capabilities
- Suggest concrete remediation steps: CLI commands, config changes, code patches.
- Provide runbook-style instructions with numbered steps.
- Generate code/config snippets (JSON, YAML, shell, Python, etc.) in fenced \
  code blocks so the operator can copy-paste them.
- Explain root cause hypotheses and how to validate them.
- Recommend which systems to check, what logs to look at, and what metrics to \
  watch.

### Rules
1. Always ground your advice in the incident context provided below.
2. Be concise and actionable — operators are under pressure.
3. Use fenced code blocks (```lang) for any commands, configs, or code.
4. If you are unsure, say so — never fabricate runbook URLs or system names.
5. If the operator asks you to "push a fix" or "apply this", describe exactly \
   what would change and ask for confirmation before saying it is done.
6. Format TODOs as markdown checklists (- [ ] item) so they render properly.

### Current incident context
{incident_context}
"""


def _build_incident_context(incident: Incident, db: Session) -> str:
    """Build a rich context string from the incident and its related data."""
    parts = [
        f"Incident ID: {incident.id}",
        f"Title: {incident.title}",
        f"Severity: {incident.severity}",
        f"Status: {incident.status}",
        f"Source: {incident.source}",
        f"Summary: {incident.summary or 'N/A'}",
        f"Severity Reasoning: {incident.severity_reasoning or 'N/A'}",
    ]

    domains = json.loads(incident.probable_domains_json) if incident.probable_domains_json else []
    if domains:
        parts.append(f"Domains: {', '.join(domains)}")

    impacted = json.loads(incident.impacted_systems_json) if incident.impacted_systems_json else []
    if impacted:
        parts.append(f"Impacted Systems: {', '.join(impacted)}")

    parts.append(f"\nOriginal Slack Message:\n{incident.raw_text or 'N/A'}")

    # Known issues
    ki_matches = db.query(KnownIssueMatch).filter(KnownIssueMatch.incident_id == incident.id).all()
    if ki_matches:
        parts.append("\nMatched Known Issues:")
        for m in ki_matches:
            ki = db.query(KnownIssue).filter(KnownIssue.id == m.known_issue_id).first()
            if ki:
                parts.append(
                    f"  - {ki.title} (match: {m.match_score:.0%})\n"
                    f"    Symptoms: {ki.symptoms or 'N/A'}\n"
                    f"    Root Cause: {ki.root_cause_summary or 'N/A'}\n"
                    f"    Remediation: {ki.remediation_steps or 'N/A'}"
                )

    # Planned actions
    actions = db.query(PlannedAction).filter(PlannedAction.incident_id == incident.id).all()
    if actions:
        parts.append("\nPlanned Actions:")
        for a in actions:
            parts.append(
                f"  - [{a.approval_status}] {a.title} ({a.action_type}, risk={a.risk_level})\n"
                f"    {a.description or ''}"
            )

    return "\n".join(parts)


@router.post("/{incident_id}")
def chat_with_agent(
    incident_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_scopes(READ_INCIDENTS)),
):
    """Send a message to the AI agent in the context of an incident."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    user_message = body.get("message", "").strip()
    conversation_history = body.get("history", [])

    if not user_message:
        raise HTTPException(status_code=400, detail="message is required")

    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")

    incident_context = _build_incident_context(incident, db)
    system = SYSTEM_PROMPT.format(incident_context=incident_context)

    # Build messages array from conversation history + new message
    messages = []
    for entry in conversation_history:
        role = entry.get("role")
        content = entry.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=settings.ANTHROPIC_MODEL or "claude-sonnet-4-5",
            max_tokens=2048,
            system=system,
            messages=messages,
        )
        reply = response.content[0].text

        operator_name = current_user.get("name") or current_user.get("email") or "Operator"
        operator_sub = current_user.get("sub")

        logger.info(
            "[CHAT] incident=%s user=%s tokens_in=%d tokens_out=%d",
            incident_id, operator_name,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        # Log the chat exchange as an audit entry
        db.add(
            AuditEntry(
                id=str(uuid.uuid4()),
                incident_id=incident_id,
                actor_type="human",
                actor_id=operator_sub,
                actor_name=operator_name,
                event_name=f"Operator asked AI agent: \"{user_message[:100]}\"",
                target_system="AI Remediation Agent",
                details_json=json.dumps({
                    "stage": "chat",
                    "user_message": user_message,
                    "ai_reply": reply,
                    "model": response.model,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "description": f"{operator_name} consulted the AI remediation agent.",
                }),
                timestamp=datetime.now(timezone.utc),
            )
        )
        db.commit()

        return {
            "data": {
                "reply": reply,
                "incidentId": incident_id,
                "model": response.model,
            },
            "error": None,
            "meta": {
                "inputTokens": response.usage.input_tokens,
                "outputTokens": response.usage.output_tokens,
            },
        }
    except Exception as e:
        logger.error("[CHAT] Failed for incident %s: %s", incident_id, e)
        raise HTTPException(status_code=500, detail=f"AI agent error: {str(e)}")
