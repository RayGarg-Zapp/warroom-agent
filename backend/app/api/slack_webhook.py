from __future__ import annotations

import hashlib
import hmac
import logging
import time

from fastapi import APIRouter, Request, HTTPException

from app.config import get_settings

router = APIRouter(prefix="/api/slack", tags=["slack"])
logger = logging.getLogger(__name__)


def _verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    """Validate the request came from Slack using the signing secret."""
    settings = get_settings()
    signing_secret = settings.SLACK_SIGNING_SECRET
    if not signing_secret:
        # If no secret configured, skip verification (dev mode)
        return True

    # Reject requests older than 5 minutes to prevent replay attacks
    if abs(time.time() - float(timestamp)) > 300:
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    computed = "v0=" + hmac.new(
        signing_secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


@router.post("/events")
async def slack_events(request: Request):
    """Handle Slack Event Subscription (challenge + message events)."""
    body_bytes = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "0")
    signature = request.headers.get("X-Slack-Signature", "")

    if not _verify_slack_signature(body_bytes, timestamp, signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    payload = await request.json()

    # Handle Slack URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload["challenge"]}

    # Handle event callbacks
    if payload.get("type") == "event_callback":
        event = payload.get("event", {})
        event_type = event.get("type")

        if event_type == "message" and not event.get("subtype"):
            text = event.get("text", "")
            channel = event.get("channel", "")

            # Simple heuristic: if the message looks like an incident report
            incident_keywords = [
                "incident", "outage", "down", "alert", "critical",
                "p1", "p0", "degraded", "failure", "error rate",
            ]
            is_incident = any(kw in text.lower() for kw in incident_keywords)

            if is_incident:
                logger.info(f"Detected potential incident from Slack channel {channel}")
                _trigger_incident_workflow(text, channel, event.get("ts"))

    return {"data": {"ok": True}, "error": None, "meta": {}}


def _trigger_incident_workflow(text: str, channel: str, message_ts: str | None):
    """Kick off the incident workflow from a Slack message."""
    import uuid
    from datetime import datetime
    from app.agents.workflow import incident_workflow

    incident_id = f"INC-{datetime.now().strftime('%Y')}-{str(uuid.uuid4())[:3].upper()}"

    initial_state = {
        "incident_id": incident_id,
        "raw_message": text,
        "source": channel,
        "slack_channel_id": channel,
        "slack_message_ts": message_ts,
        "severity": None, "confidence": None, "title": None, "summary": None,
        "severity_reasoning": None, "probable_domains": None, "impacted_systems": None,
        "responders": None, "known_issues": None, "proposed_actions": None,
        "approvals_required": None, "all_approved": None, "execution_results": None,
        "audit_entries": [], "current_stage": "ingesting", "errors": None,
    }

    try:
        result = incident_workflow.invoke(initial_state)
        logger.info(f"Workflow completed for incident {incident_id}: stage={result.get('current_stage')}")
        # Persistence is handled within the workflow nodes / inject endpoint
    except Exception as e:
        logger.error(f"Workflow failed for incident {incident_id}: {e}")
