import json
from pathlib import Path

import httpx

from app.integrations.token_vault_adapter import TokenVaultAdapter

EVIDENCE_DIR = Path(__file__).resolve().parents[2] / "data" / "evidence"


def _load_json(filename: str):
    path = EVIDENCE_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Evidence file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_threat_hunt(incident: dict, operator_context: dict) -> dict:
    """
    Analyze local seeded evidence first.
    Optionally enrich with delegated Slack evidence via Token Vault.
    """
    auth_events = _load_json("auth_events.json")
    tenant_impacts = _load_json("tenant_impacts.json")

    suspicious_events = [
        e for e in auth_events
        if e.get("event_type") in {
            "admin_session_started",
            "mfa_reset_initiated",
            "anomalous_login_failure_spike",
        }
    ]

    if not suspicious_events:
        return {
            "success": False,
            "agent": "threat_hunt_agent",
            "error": "No suspicious auth events found",
        }

    actor_counts = {}
    client_counts = {}
    tenants = set()
    evidence_refs = []

    for e in suspicious_events:
        actor = e.get("actor_user_id")
        client_id = e.get("client_id")
        tenant_id = e.get("tenant_id")

        if actor:
            actor_counts[actor] = actor_counts.get(actor, 0) + 1
        if client_id:
            client_counts[client_id] = client_counts.get(client_id, 0) + 1
        if tenant_id and tenant_id != "multiple":
            tenants.add(tenant_id)

        evidence_refs.append(f"auth_events:{e['event_id']}")

    suspicious_actor = max(actor_counts, key=actor_counts.get) if actor_counts else None
    suspicious_client = max(client_counts, key=client_counts.get) if client_counts else None

    timestamps = sorted([e["timestamp"] for e in suspicious_events if e.get("timestamp")])
    time_window = {
        "start": timestamps[0] if timestamps else None,
        "end": timestamps[-1] if timestamps else None,
    }

    impacted = [t for t in tenant_impacts if t["tenant_id"] in tenants]

    # Optional Slack evidence enrichment
    slack_evidence = []
    slack_channel_id = incident.get("slackEvidenceChannelId")

    if slack_channel_id and operator_context.get("auth0_access_token"):
        token_vault = TokenVaultAdapter()
        slack_token = token_vault.get_provider_token(
            provider="slack",
            scopes=["channels:read", "channels:history"],
            user_access_token=operator_context.get("auth0_access_token"),
            user_id=operator_context.get("sub"),
            actor_email=operator_context.get("email"),
            incident_id=incident.get("id"),
            reason=f"Threat hunt evidence read for {incident.get('id')}",
        )

        if slack_token.get("success"):
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    "https://slack.com/api/conversations.history",
                    params={"channel": slack_channel_id, "limit": 10},
                    headers={"Authorization": f"Bearer {slack_token['access_token']}"},
                )
                data = resp.json()
                if data.get("ok"):
                    for msg in data.get("messages", [])[:3]:
                        slack_evidence.append(
                            {
                                "ts": msg.get("ts"),
                                "text": msg.get("text", "")[:300],
                            }
                        )
                        evidence_refs.append(f"slack:{slack_channel_id}:{msg.get('ts')}")

    return {
        "success": True,
        "agent": "threat_hunt_agent",
        "suspicious_actor": suspicious_actor,
        "suspicious_client": suspicious_client,
        "affected_tenants": [t["tenant_id"] for t in impacted],
        "time_window_utc": time_window,
        "evidence_references": evidence_refs,
        "slack_evidence": slack_evidence,
        "confidence": 0.93,
        "recommended_containment": {
            "action": "disable_client_and_revoke_sessions",
            "target_client_id": suspicious_client,
            "target_user_id": suspicious_actor,
        },
    }