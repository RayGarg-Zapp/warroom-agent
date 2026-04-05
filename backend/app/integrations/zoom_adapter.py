from __future__ import annotations

import json
import logging
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)

class ZoomAdapter:
    """Zoom integration adapter for creating war room meetings."""

    def __init__(self):
        self.settings = get_settings()
        self.client_id = self.settings.ZOOM_CLIENT_ID
        self.client_secret = self.settings.ZOOM_CLIENT_SECRET
        self.account_id = self.settings.ZOOM_ACCOUNT_ID

    @property
    def is_live(self) -> bool:
        return bool(self.client_id and self.client_secret and self.account_id)

    def _get_access_token(self) -> str | None:
        """Get OAuth token using server-to-server flow."""
        # TODO: Integrate with Auth0 Token Vault when available
        try:
            with httpx.Client() as client:
                resp = client.post(
                    "https://zoom.us/oauth/token",
                    params={"grant_type": "account_credentials", "account_id": self.account_id},
                    auth=(self.client_id, self.client_secret)
                )
                return resp.json().get("access_token")
        except Exception as e:
            logger.error(f"Zoom token fetch failed: {e}")
            return None

    def create_meeting(self, action) -> dict:
        """Create a Zoom meeting for the war room."""
        metadata_json = action.metadata_json if hasattr(action, 'metadata_json') else "{}"
        metadata = json.loads(metadata_json) if isinstance(metadata_json, str) else metadata_json

        topic = metadata.get("topic", action.title)
        duration = int(metadata.get("duration", "60"))

        if not self.is_live:
            mock_url = f"https://zoom.us/j/mock-{action.id[:8]}"
            logger.info(f"[MOCK] Zoom meeting created: {topic} -> {mock_url}")
            return {"success": True, "mock": True, "join_url": mock_url, "topic": topic}

        token = self._get_access_token()
        if not token:
            return {"success": False, "error": "Could not obtain Zoom access token"}

        try:
            with httpx.Client() as client:
                resp = client.post(
                    "https://api.zoom.us/v2/users/me/meetings",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "topic": topic,
                        "type": 1,  # Instant meeting
                        "duration": duration,
                        "settings": {"join_before_host": True, "waiting_room": False}
                    }
                )
                data = resp.json()
                return {"success": True, "join_url": data.get("join_url", ""), "meeting_id": data.get("id")}
        except Exception as e:
            logger.error(f"Zoom meeting creation failed: {e}")
            return {"success": False, "error": str(e)}
