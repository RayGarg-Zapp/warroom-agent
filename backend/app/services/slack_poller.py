from __future__ import annotations

"""
Slack Channel Poller — pull-based incident detection.

Periodically calls Slack's conversations.history API to fetch new messages
from a configured channel.  An Anthropic Claude agent decides whether each
message (or group of consecutive messages from the same user) is a real
incident or just conversation / inquiry.  Only confirmed incidents trigger
the full workflow and are persisted to the DB.
"""

import asyncio
import json as _json
import logging
import time
import uuid
from datetime import datetime, timezone

import anthropic
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)

# Track the timestamp of the last message we processed so we only fetch new ones.
_last_seen_ts: str | None = None

# Buffer consecutive messages from the same user so multi-line posts are
# treated as a single incident report.
_msg_buffer: list[dict] = []
_buffer_user: str | None = None
# How many seconds between messages from the same user before we flush the buffer
_MULTILINE_WINDOW = 30.0

# ── AI triage prompt ──────────────────────────────────────────────────────────

TRIAGE_PROMPT = """\
You are WarRoom Agent's intake triage system.  Your ONLY job is to decide
whether a Slack message describes an actual operational incident that needs
an automated incident-response workflow.

### What IS an incident (respond "yes")
- Service outages, partial outages, severe degradation
- P1 / P2 production alerts (error-rate spikes, latency, downtime)
- Security breaches, data loss, certificate failures, DNS failures
- Payment processing failures, login / auth outages
- Infrastructure failures (database down, CDN stale, cloud region issue)
- Any message that reports a live, ongoing problem affecting users or systems

### What is NOT an incident (respond "no")
- General questions or inquiries ("has anyone seen issues with X?", "is the API slow for anyone else?")
- Casual conversation, greetings, status updates ("I'm looking into it", "thanks for the update")
- Requests for help that aren't reporting a live issue ("can someone help me deploy?")
- FYI / informational messages with no urgency
- Messages discussing past incidents that are already resolved ("last week's outage was caused by...")
- Bot messages, join/leave notifications
- Testing messages ("just testing the channel", "hello world")

### Reference: Real incident examples from our system
These are examples of REAL incidents that our system has handled before.
Use these to calibrate what a genuine incident report looks like:

{demo_incidents}

### Reference: Known issues in our environment
These are known operational issues in our infrastructure. Messages reporting
symptoms matching these are very likely real incidents:

{known_issues}

### Message to evaluate
{message}

### Required JSON output (no markdown fences, pure JSON)
{{
  "is_incident": true | false,
  "reasoning": "one sentence explaining your decision"
}}

Return ONLY valid JSON — no preamble, no commentary.
"""


def _load_reference_data() -> tuple[str, str]:
    """Load demo incidents and known issues JSON files for the triage prompt."""
    import pathlib

    base = pathlib.Path(__file__).resolve().parent.parent.parent / "data"

    demo_path = base / "demo" / "demo_incidents.json"
    known_path = base / "seed" / "known_issues.json"

    try:
        demo_incidents = _json.loads(demo_path.read_text())
        # Extract only the fields relevant for triage
        demo_summary = _json.dumps(
            [
                {
                    "raw_text": d.get("raw_text", ""),
                    "severity": d.get("severity", ""),
                    "title": d.get("title", ""),
                }
                for d in demo_incidents
            ],
            indent=2,
        )
    except Exception as e:
        logger.warning("[TRIAGE] Could not load demo_incidents.json: %s", e)
        demo_summary = "[]"

    try:
        known_issues = _json.loads(known_path.read_text())
        known_summary = _json.dumps(
            [
                {
                    "title": ki.get("title", ""),
                    "symptoms": ki.get("symptoms", ""),
                    "severity_hint": ki.get("severity_hint", ""),
                    "domain": ki.get("domain", ""),
                    "keywords": ki.get("keywords_json", []),
                }
                for ki in known_issues
            ],
            indent=2,
        )
    except Exception as e:
        logger.warning("[TRIAGE] Could not load known_issues.json: %s", e)
        known_summary = "[]"

    return demo_summary, known_summary


def _ai_is_incident(text: str) -> bool:
    """Use Claude to decide whether *text* describes a real incident."""
    settings = get_settings()
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        logger.warning("[TRIAGE] No ANTHROPIC_API_KEY — falling back to keyword match")
        return _keyword_fallback(text)

    demo_incidents, known_issues = _load_reference_data()

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[
                {
                    "role": "user",
                    "content": TRIAGE_PROMPT.format(
                        message=text,
                        demo_incidents=demo_incidents,
                        known_issues=known_issues,
                    ),
                }
            ],
        )
        raw = response.content[0].text.strip()
        logger.debug("[TRIAGE] Raw AI response: %s", raw)

        # Strip markdown fences if the model wraps its output
        import re
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        result = _json.loads(cleaned)
        is_incident = result.get("is_incident", False)
        reasoning = result.get("reasoning", "")
        logger.info(
            "[TRIAGE] is_incident=%s reasoning=%s",
            is_incident, reasoning,
        )
        return bool(is_incident)
    except Exception as e:
        logger.error("[TRIAGE] AI triage failed (%s) — defaulting to NOT incident", e)
        return False


def _keyword_fallback(text: str) -> bool:
    """Simple keyword check used when AI triage is unavailable."""
    keywords = [
        "incident", "outage", "down", "alert", "critical",
        "p1", "p0", "degraded", "failure", "error rate",
    ]
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


# ── Multi-line buffer helpers ─────────────────────────────────────────────────

def _flush_buffer() -> tuple[str, str, str | None] | None:
    """Collapse buffered messages into one text block.  Returns (text, user, ts) or None."""
    global _msg_buffer, _buffer_user
    if not _msg_buffer:
        return None
    combined_text = "\n".join(m["text"] for m in _msg_buffer)
    first_ts = _msg_buffer[0]["ts"]
    user = _buffer_user
    _msg_buffer = []
    _buffer_user = None
    return combined_text, user, first_ts


def _buffer_message(msg: dict) -> tuple[str, str, str | None] | None:
    """Add a message to the buffer.  Returns a flushed block if the buffer
    should be processed (different user or time gap exceeded)."""
    global _msg_buffer, _buffer_user

    user = msg.get("user", "unknown")
    ts = float(msg.get("ts", "0"))

    # If same user and within time window, keep buffering
    if _buffer_user == user and _msg_buffer:
        last_ts = float(_msg_buffer[-1].get("ts", "0"))
        if ts - last_ts <= _MULTILINE_WINDOW:
            _msg_buffer.append(msg)
            return None

    # Different user or time gap — flush previous buffer and start new one
    flushed = _flush_buffer()
    _buffer_user = user
    _msg_buffer = [msg]
    return flushed


# ── Workflow + DB persistence ─────────────────────────────────────────────────

def _trigger_incident_workflow(text: str, channel: str, message_ts: str | None):
    """Kick off the incident workflow and persist everything to the DB."""
    from app.agents.workflow import incident_workflow
    from app.database import SessionLocal
    from app.models.incident import Incident
    from app.models.planned_action import PlannedAction
    from app.models.responder_assignment import ResponderAssignment
    from app.models.known_issue_match import KnownIssueMatch
    from app.models.audit_entry import AuditEntry

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
        logger.info(
            "Workflow completed for incident %s: stage=%s",
            incident_id, result.get("current_stage"),
        )
    except Exception as e:
        logger.error("Workflow failed for incident %s: %s", incident_id, e)
        return

    # ── Persist to DB ──────────────────────────────────────────────────
    db = SessionLocal()
    try:
        incident = Incident(
            id=incident_id,
            source=channel,
            raw_text=text,
            title=result.get("title") or "Untitled Incident",
            severity=result.get("severity") or "P2",
            confidence=result.get("confidence") or 0.0,
            summary=result.get("summary") or "",
            severity_reasoning=result.get("severity_reasoning") or "",
            probable_domains_json=_json.dumps(result.get("probable_domains") or []),
            impacted_systems_json=_json.dumps(result.get("impacted_systems") or []),
            status=(
                result.get("current_stage", "awaiting_approval")
                if result.get("approvals_required")
                else "in_progress"
            ),
        )
        db.add(incident)
        db.flush()

        for r_data in (result.get("responders") or []):
            db.add(
                ResponderAssignment(
                    id=str(uuid.uuid4()),
                    incident_id=incident_id,
                    responder_id=r_data["id"],
                    confidence=r_data.get("confidence", 0.0),
                    assignment_role="primary",
                )
            )

        for ki_data in (result.get("known_issues") or []):
            db.add(
                KnownIssueMatch(
                    id=str(uuid.uuid4()),
                    incident_id=incident_id,
                    known_issue_id=ki_data["id"],
                    match_score=ki_data.get("matchScore", 0.0),
                )
            )

        for a_data in (result.get("proposed_actions") or []):
            db.add(
                PlannedAction(
                    id=str(uuid.uuid4()),
                    incident_id=incident_id,
                    action_type=a_data.get("action_type", ""),
                    title=a_data.get("title", ""),
                    description=a_data.get("description", ""),
                    target_system=a_data.get("provider", ""),
                    risk_level=a_data.get("risk_level", "medium"),
                    approval_required=a_data.get("risk_level", "medium") in ("high", "critical"),
                    approval_status="pending",
                    execution_status="pending",
                    provider=a_data.get("provider", ""),
                    scopes_used_json=_json.dumps(a_data.get("scopes_used", [])),
                    recipients_json=_json.dumps(a_data.get("recipients", [])),
                    metadata_json=_json.dumps(a_data.get("metadata", {})),
                )
            )

        for ae_data in (result.get("audit_entries") or []):
            db.add(
                AuditEntry(
                    id=str(uuid.uuid4()),
                    incident_id=incident_id,
                    actor_type=ae_data.get("actor_type", "system"),
                    actor_name=ae_data.get("actor_name", "WarRoom Agent"),
                    event_name=ae_data.get("event", ""),
                    target_system=ae_data.get("target_system", ""),
                    details_json=ae_data.get("details_json"),
                    timestamp=(
                        datetime.fromisoformat(ae_data["timestamp"].replace("Z", "+00:00"))
                        if ae_data.get("timestamp")
                        else datetime.now(timezone.utc)
                    ),
                )
            )

        db.add(
            AuditEntry(
                id=str(uuid.uuid4()),
                incident_id=incident_id,
                actor_type="system",
                actor_name="Slack Poller",
                event_name=f"Incident detected from Slack channel {channel}: {incident.title}",
                target_system=channel,
                timestamp=datetime.now(timezone.utc),
            )
        )

        db.commit()
        logger.info("[DB PERSISTED] Incident %s saved to database", incident_id)

        # Grant default approvers in FGA
        try:
            from app.security.fga_client import fga_client
            fga_client.grant_incident_approvers(incident_id)
        except Exception as fga_err:
            logger.warning("[FGA] Failed to grant approvers for %s: %s", incident_id, fga_err)

    except Exception as e:
        db.rollback()
        logger.error("[DB ERROR] Failed to persist incident %s: %s", incident_id, e)
    finally:
        db.close()


# ── Process a completed message block ─────────────────────────────────────────

def _process_message_block(text: str, user: str, channel_id: str, ts: str | None):
    """Run AI triage on a message block; trigger workflow if it's a real incident."""
    logger.debug(
        "[SLACK MSG] channel=%s user=%s ts=%s text=%s",
        channel_id, user, ts, text[:120],
    )

    if _ai_is_incident(text):
        logger.info(
            "[INCIDENT CONFIRMED] channel=%s ts=%s text=%s",
            channel_id, ts, text[:80],
        )
        _trigger_incident_workflow(text, channel_id, ts)
    else:
        logger.debug(
            "[NOT INCIDENT] channel=%s ts=%s — skipped by AI triage",
            channel_id, ts,
        )


# ── Polling loop ──────────────────────────────────────────────────────────────

async def _poll_once(channel_id: str, token: str) -> None:
    """Fetch new messages from the channel and process any that look like incidents."""
    global _last_seen_ts

    params: dict = {"channel": channel_id, "limit": 20}
    if _last_seen_ts:
        params["oldest"] = _last_seen_ts

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://slack.com/api/conversations.history",
            headers=headers,
            params=params,
        )
        data = resp.json()

    if not data.get("ok"):
        logger.error("Slack conversations.history error: %s", data.get("error"))
        return

    messages = data.get("messages", [])
    if messages:
        logger.debug(
            "[POLLER] Fetched %d messages from channel %s (oldest=%s)",
            len(messages), channel_id, params.get("oldest"),
        )
    if not messages:
        # No new messages — flush any remaining buffer from previous poll
        flushed = _flush_buffer()
        if flushed:
            text, user, ts = flushed
            _process_message_block(text, user, channel_id, ts)
        return

    # Messages come newest-first; process oldest-first
    messages.sort(key=lambda m: float(m.get("ts", "0")))

    for msg in messages:
        # Skip bot messages, subtypes (joins, edits, etc.)
        if msg.get("subtype") or msg.get("bot_id"):
            continue

        flushed = _buffer_message(msg)
        if flushed:
            text, user, ts = flushed
            _process_message_block(text, user, channel_id, ts)

    # Flush remaining buffer at end of poll cycle
    flushed = _flush_buffer()
    if flushed:
        text, user, ts = flushed
        _process_message_block(text, user, channel_id, ts)

    # Advance the cursor to the newest message we just saw
    _last_seen_ts = messages[-1].get("ts")


async def start_polling():
    """Long-running coroutine that polls Slack on the configured interval."""
    settings = get_settings()
    channel_id = settings.SLACK_CHANNEL_ID
    token = settings.SLACK_BOT_TOKEN
    interval = settings.SLACK_POLL_INTERVAL

    if not channel_id:
        logger.warning("SLACK_CHANNEL_ID not set — Slack poller disabled")
        return
    if not token:
        logger.warning("SLACK_BOT_TOKEN not set — Slack poller disabled")
        return

    logger.info(
        "Slack poller started: channel=%s, interval=%ds", channel_id, interval,
    )

    # Seed _last_seen_ts to "now" so we don't re-process old history on first boot.
    # Use integer precision — Slack's API mishandles high-precision floats from time.time().
    global _last_seen_ts
    _last_seen_ts = str(int(time.time()))

    while True:
        try:
            await _poll_once(channel_id, token)
        except Exception as e:
            logger.error("Slack poller error: %s", e)

        await asyncio.sleep(interval)