from __future__ import annotations

import json
import logging

import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)


class SlackAdapter:
    """Slack integration adapter. Uses delegated token when provided, bot token otherwise."""

    def __init__(self):
        self.settings = get_settings()
        self.token = self.settings.SLACK_BOT_TOKEN
        self.base_url = "https://slack.com/api"

    def send_dm(self, action, access_token: str | None = None, token_context: dict | None = None) -> dict:
        recipients_json = action.recipients_json if hasattr(action, "recipients_json") else "[]"
        recipients = json.loads(recipients_json) if isinstance(recipients_json, str) else recipients_json

        metadata_json = action.metadata_json if hasattr(action, "metadata_json") else "{}"
        metadata = json.loads(metadata_json) if isinstance(metadata_json, str) else metadata_json
        zoom_join_url = metadata.get("zoom_join_url")

        active_token = access_token or self.token
        auth_mode = (
            "delegated-token-vault"
            if access_token
            else "system-bot-token"
            if self.token
            else "mock"
        )

        if not active_token:
            logger.info("[MOCK] Slack DM to %s", recipients)
            return {
                "success": True,
                "mock": True,
                "auth_mode": "mock",
                "message": f"Mock DM sent to {len(recipients)} recipients",
            }

        try:
            results = []

            message_text = f"🚨 *Incident Alert* — {action.title}\n\n{action.description}"
            if zoom_join_url:
                message_text += f"\n\nZoom Join URL: {zoom_join_url}"

            headers = {
                "Authorization": f"Bearer {active_token}",
                "Content-Type": "application/json; charset=utf-8",
            }

            with httpx.Client(timeout=15.0) as client:
                for recipient in recipients:
                    conv_resp = client.post(
                        f"{self.base_url}/conversations.open",
                        headers=headers,
                        json={"users": recipient},
                    )
                    conv_data = conv_resp.json()
                    channel = conv_data.get("channel", {}).get("id")

                    if not channel:
                        results.append({
                            "ok": False,
                            "recipient": recipient,
                            "error": conv_data,
                        })
                        continue

                    msg_resp = client.post(
                        f"{self.base_url}/chat.postMessage",
                        headers=headers,
                        json={
                            "channel": channel,
                            "text": message_text,
                        },
                    )
                    results.append(msg_resp.json())

            return {
                "success": True,
                "results": results,
                "auth_mode": auth_mode,
                "token_context": {
                    "provider": token_context.get("provider") if token_context else None,
                    "mode": token_context.get("mode") if token_context else None,
                },
            }
        except Exception as e:
            logger.error("Slack DM failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "auth_mode": auth_mode,
            }

    def post_message(self, channel: str, text: str, access_token: str | None = None) -> dict:
        active_token = access_token or self.token
        auth_mode = (
            "delegated-token-vault"
            if access_token
            else "system-bot-token"
            if self.token
            else "mock"
        )

        if not active_token:
            logger.info("[MOCK] Slack post to %s: %s...", channel, text[:50])
            return {"success": True, "mock": True, "auth_mode": "mock"}

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(
                    f"{self.base_url}/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {active_token}",
                        "Content-Type": "application/json; charset=utf-8",
                    },
                    json={"channel": channel, "text": text},
                )
                return {
                    "success": resp.json().get("ok", False),
                    "data": resp.json(),
                    "auth_mode": auth_mode,
                }
        except Exception as e:
            return {"success": False, "error": str(e), "auth_mode": auth_mode}