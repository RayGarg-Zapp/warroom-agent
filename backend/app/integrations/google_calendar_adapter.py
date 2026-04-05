from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from app.config import get_settings

logger = logging.getLogger(__name__)


class GoogleCalendarAdapter:
    """
    Google Calendar adapter.

    Modes:
    - delegated-token-vault: uses the linked user's Google token and writes to that user's primary calendar
    - system-service-account: uses the existing service account and can still target a configured/shared calendar
    - mock: no live credentials available
    """

    def __init__(self):
        self.settings = get_settings()
        self.service_account_key = self.settings.GOOGLE_SERVICE_ACCOUNT_KEY

    @property
    def is_live_service_account(self) -> bool:
        return bool(self.service_account_key)

    def create_event(self, action, access_token: str | None = None, token_context: dict | None = None) -> dict:
        metadata_json = action.metadata_json if hasattr(action, "metadata_json") else "{}"
        metadata = json.loads(metadata_json) if isinstance(metadata_json, str) else (metadata_json or {})

        recipients_json = action.recipients_json if hasattr(action, "recipients_json") else "[]"
        recipients = json.loads(recipients_json) if isinstance(recipients_json, str) else (recipients_json or [])

        event_title = metadata.get("title", action.title)
        duration = int(metadata.get("duration", "60"))
        requested_calendar_id = metadata.get("calendar_id")
        zoom_join_url = metadata.get("zoom_join_url")

        try:
            from googleapiclient.discovery import build
        except ImportError:
            return {
                "success": False,
                "error": "Missing Google Calendar dependencies. Install google-api-python-client and google-auth.",
            }

        auth_mode = "mock"
        credentials = None

        if access_token:
            try:
                from google.oauth2.credentials import Credentials

                credentials = Credentials(token=access_token)
                auth_mode = "delegated-token-vault"
            except Exception as e:
                return {"success": False, "error": f"Delegated Google credential init failed: {e}"}

        elif self.is_live_service_account:
            try:
                from google.oauth2 import service_account

                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_key,
                    scopes=["https://www.googleapis.com/auth/calendar"],
                )
                auth_mode = "system-service-account"
            except Exception as e:
                return {"success": False, "error": f"Service account init failed: {e}"}

        if not credentials:
            logger.info("[MOCK] Google Calendar event: %s for %s attendees", event_title, len(recipients))
            return {
                "success": True,
                "mock": True,
                "auth_mode": "mock",
                "event_title": event_title,
                "attendees": recipients,
                "calendar_link": f"https://calendar.google.com/mock-event-{action.id[:8]}",
            }

        # Critical fix:
        # Delegated Token Vault flow should write to the linked user's own calendar.
        # If old metadata still contains a hard-coded shared/group calendar, ignore it here.
        if auth_mode == "delegated-token-vault":
            calendar_id = "primary"
            if requested_calendar_id and requested_calendar_id != "primary":
                logger.info(
                    "[GOOGLE] overriding metadata calendar_id=%s -> primary for delegated Token Vault flow",
                    requested_calendar_id,
                )
        else:
            calendar_id = requested_calendar_id or "primary"

        try:
            service = build("calendar", "v3", credentials=credentials, cache_discovery=False)

            start_dt = datetime.now(timezone.utc) + timedelta(minutes=2)
            end_dt = start_dt + timedelta(minutes=duration)

            description_lines = [
                f"Incident: {action.title}",
                action.description or "",
                "",
                "Organizer mode:",
                auth_mode,
                "",
                "Intended recipients:",
                ", ".join(recipients) if recipients else "None",
            ]

            if zoom_join_url:
                description_lines.append("")
                description_lines.append(f"Zoom Join URL: {zoom_join_url}")

            event_body = {
                "summary": event_title,
                "description": "\n".join(description_lines).strip(),
                "start": {
                    "dateTime": start_dt.isoformat(),
                    "timeZone": "UTC",
                },
                "end": {
                    "dateTime": end_dt.isoformat(),
                    "timeZone": "UTC",
                },
            }

            insert_kwargs = {
                "calendarId": calendar_id,
                "body": event_body,
            }

            # For the MVP pattern, the linked operator calendar is the organizer calendar.
            # Add recipients as attendees so they get invitations.
            if recipients:
                event_body["attendees"] = [{"email": email} for email in recipients]
                insert_kwargs["sendUpdates"] = "all"

            logger.info(
                "[GOOGLE] creating event auth_mode=%s calendar_id=%s attendees=%s",
                auth_mode,
                calendar_id,
                len(recipients),
            )

            event = service.events().insert(**insert_kwargs).execute()

            return {
                "success": True,
                "event_id": event.get("id"),
                "calendar_link": event.get("htmlLink"),
                "attendees": recipients,
                "calendar_id_used": calendar_id,
                "auth_mode": auth_mode,
                "token_context": {
                    "provider": token_context.get("provider") if token_context else None,
                    "mode": token_context.get("mode") if token_context else None,
                },
            }

        except Exception as e:
            logger.error("Google Calendar event creation failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "calendar_id_used": calendar_id,
                "auth_mode": auth_mode,
            }