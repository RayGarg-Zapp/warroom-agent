from __future__ import annotations

import logging
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)

class Auth0Service:
    """
    Auth0 integration service.

    Handles:
    - User identity verification
    - Connected account status checking
    - Delegated consent validation
    - Step-up authentication signals

    NOTE: This is the adapter boundary for Auth0 for AI Agents.
    Token Vault interactions go through TokenVaultAdapter.
    """

    def __init__(self):
        self.settings = get_settings()
        self.domain = self.settings.AUTH0_DOMAIN
        self.client_id = self.settings.AUTH0_CLIENT_ID
        self.client_secret = self.settings.AUTH0_CLIENT_SECRET
        self.audience = self.settings.AUTH0_AUDIENCE

    @property
    def is_configured(self) -> bool:
        return bool(self.domain and self.client_id)

    def get_management_token(self) -> str | None:
        """Get Auth0 Management API token."""
        if not self.is_configured:
            logger.info("[MOCK] Auth0 not configured, returning mock token")
            return "mock-auth0-mgmt-token"

        try:
            with httpx.Client() as client:
                resp = client.post(
                    f"https://{self.domain}/oauth/token",
                    json={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "audience": f"https://{self.domain}/api/v2/",
                        "grant_type": "client_credentials"
                    }
                )
                return resp.json().get("access_token")
        except Exception as e:
            logger.error(f"Auth0 token fetch failed: {e}")
            return None

    def verify_user_identity(self, user_id: str) -> dict:
        """Verify user identity via Auth0."""
        if not self.is_configured:
            return {"verified": True, "mock": True, "user_id": user_id}
        # TODO: Real Auth0 user verification
        return {"verified": True, "user_id": user_id}

    def check_connected_account(self, user_id: str, provider: str) -> dict:
        """Check if user has a connected account for a provider."""
        if not self.is_configured:
            return {"connected": True, "mock": True, "provider": provider}
        # TODO: Real connected account check via Auth0 API
        return {"connected": False, "provider": provider}

    def request_step_up_auth(self, user_id: str, reason: str) -> dict:
        """Request step-up authentication for high-risk actions."""
        if not self.is_configured:
            logger.info(f"[MOCK] Step-up auth requested for {user_id}: {reason}")
            return {"required": True, "mock": True, "challenge_id": "mock-challenge"}
        # TODO: Real step-up auth via Auth0 MFA API
        return {"required": True, "challenge_id": "pending"}
