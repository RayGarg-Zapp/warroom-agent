import httpx

from app.integrations.token_vault_adapter import TokenVaultAdapter
from app.services.agent_auth import get_agent_access_token


def run_session_containment(
    incident: dict,
    operator_context: dict,
    hunt_result: dict,
    app_base_url: str,
) -> dict:
    """
    Use Auth0 M2M for first-party identity control APIs.
    Use Token Vault only for delegated Slack posting.
    """
    recommended = hunt_result.get("recommended_containment", {})
    target_user_id = recommended.get("target_user_id")
    target_client_id = recommended.get("target_client_id")

    agent_token = get_agent_access_token("identity:revoke_sessions identity:disable_client")

    revoke_result = None
    disable_result = None

    with httpx.Client(timeout=20.0) as client:
        if target_user_id:
            revoke_resp = client.post(
                f"{app_base_url}/api/identity/revoke-sessions",
                json={
                    "incident_id": incident["id"],
                    "target_user_id": target_user_id,
                },
                headers={"Authorization": f"Bearer {agent_token['access_token']}"},
            )
            revoke_resp.raise_for_status()
            revoke_result = revoke_resp.json()["data"]

        if target_client_id:
            disable_resp = client.post(
                f"{app_base_url}/api/identity/disable-client",
                json={
                    "incident_id": incident["id"],
                    "target_client_id": target_client_id,
                },
                headers={"Authorization": f"Bearer {agent_token['access_token']}"},
            )
            disable_resp.raise_for_status()
            disable_result = disable_resp.json()["data"]

    slack_post = None
    slack_channel_id = incident.get("slackContainmentChannelId")

    if operator_context.get("auth0_access_token") and slack_channel_id:
        token_vault = TokenVaultAdapter()
        slack_token = token_vault.get_provider_token(
            provider="slack",
            scopes=["chat:write"],
            user_access_token=operator_context.get("auth0_access_token"),
            user_id=operator_context.get("sub"),
            actor_email=operator_context.get("email"),
            incident_id=incident["id"],
            reason=f"Containment notification for {incident['id']}",
        )

        if slack_token.get("success"):
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    "https://slack.com/api/chat.postMessage",
                    json={
                        "channel": slack_channel_id,
                        "text": (
                            f":rotating_light: Session Containment Agent executed containment for {incident['id']}\n"
                            f"- suspicious_actor: {hunt_result.get('suspicious_actor')}\n"
                            f"- suspicious_client: {hunt_result.get('suspicious_client')}\n"
                            f"- affected_tenants: {', '.join(hunt_result.get('affected_tenants', []))}\n"
                            f"- action: revoke sessions + disable client"
                        ),
                    },
                    headers={"Authorization": f"Bearer {slack_token['access_token']}"},
                )
                slack_post = resp.json()

    return {
        "success": True,
        "agent": "session_containment_agent",
        "agent_auth": {
            "client_id": agent_token.get("client_id"),
            "scope": agent_token.get("scope"),
        },
        "revoke_result": revoke_result,
        "disable_result": disable_result,
        "slack_post": slack_post,
    }