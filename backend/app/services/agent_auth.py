import httpx
from app.config import get_settings


def get_agent_access_token(scope: str) -> dict:
    """
    Mint an Auth0 client-credentials token for the agent tier.

    This proves the machine actor identity when calling our own first-party APIs.
    It is NOT used for Token Vault exchange with Slack/Google.
    """
    settings = get_settings()

    token_url = f"https://{settings.AUTH0_DOMAIN}/oauth/token"
    audience = settings.AUTH0_AUDIENCE

    payload = {
        "grant_type": "client_credentials",
        "client_id": settings.AUTH0_AGENT_CLIENT_ID,
        "client_secret": settings.AUTH0_AGENT_CLIENT_SECRET,
        "audience": audience,
        "scope": scope,
    }

    with httpx.Client(timeout=15.0) as client:
        response = client.post(token_url, json=payload)
        response.raise_for_status()
        data = response.json()

    return {
        "access_token": data["access_token"],
        "token_type": data.get("token_type", "Bearer"),
        "scope": data.get("scope", scope),
        "expires_in": data.get("expires_in"),
        "client_id": settings.AUTH0_AGENT_CLIENT_ID,
    }