import hashlib
import hmac
import time
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)

def validate_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    """Validate Slack request signature."""
    settings = get_settings()
    if not settings.SLACK_SIGNING_SECRET:
        logger.warning("SLACK_SIGNING_SECRET not set, skipping validation")
        return True  # Allow in dev mode

    # Check timestamp freshness (within 5 minutes)
    if abs(time.time() - float(timestamp)) > 300:
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    computed = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed, signature)

def normalize_slack_message(payload: dict) -> dict:
    """Extract and normalize relevant fields from Slack event payload."""
    event = payload.get("event", {})
    return {
        "raw_text": event.get("text", ""),
        "channel_id": event.get("channel", ""),
        "message_ts": event.get("ts", ""),
        "user_id": event.get("user", ""),
        "source": f"#{event.get('channel', 'unknown')}",
    }

def is_incident_message(text: str) -> bool:
    """Quick check if a message looks like an incident report."""
    incident_indicators = [
        "p1", "p2", "incident", "outage", "down", "degraded",
        "failure", "cannot", "impacted", "alert", "critical"
    ]
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in incident_indicators)
