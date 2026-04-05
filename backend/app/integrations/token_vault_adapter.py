from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class TokenVaultAdapter:
    """
    Auth0 Token Vault adapter.

    Design:
    - Slack, Google, and GitHub are vault-backed providers.
    - Zoom and SMTP stay system-owned for now.
    - The backend exchanges the signed-in operator's Auth0 access token
      for a provider token using Auth0's /oauth/token endpoint and
      the confidential Custom API Client ("Broker").
    - No raw provider refresh token is stored in this app.
    """

    VAULT_BACKED_PROVIDERS = {"google", "slack", "github"}
    SYSTEM_OWNED_PROVIDERS = {"zoom", "smtp", "email"}

    TOKEN_EXCHANGE_GRANT = (
        "urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token"
    )
    SUBJECT_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"
    REQUESTED_TOKEN_TYPE = "http://auth0.com/oauth/token-type/federated-connection-access-token"

    GOOGLE_SCOPE_MAP = {
        "calendar": "https://www.googleapis.com/auth/calendar",
        "calendar.read": "https://www.googleapis.com/auth/calendar.readonly",
        "calendar.events": "https://www.googleapis.com/auth/calendar.events",
        "calendar.events.write": "https://www.googleapis.com/auth/calendar.events",
        "calendar.events.read": "https://www.googleapis.com/auth/calendar.events.readonly",
        "calendar.events.readonly": "https://www.googleapis.com/auth/calendar.events.readonly",
        "calendar.settings.read": "https://www.googleapis.com/auth/calendar.settings.readonly",
    }

    SLACK_SCOPE_MAP = {
        "channels:history": "channels:history",
        "channels:read": "channels:read",
        "chat:write": "chat:write",
        "im:write": "im:write",
        "users:read": "users:read",
    }

    # GitHub note:
    # Auth0's GitHub AI integration docs currently note that scopes are not supported
    # dynamically for GitHub in the same way as some other providers. So we support
    # GitHub provider exchange, but do not push per-request scopes through this adapter yet.
    GITHUB_SCOPE_MAP = {}

    def __init__(self):
        settings = get_settings()

        self.auth0_domain = getattr(settings, "AUTH0_DOMAIN", None)
        self.auth0_token_endpoint = getattr(settings, "AUTH0_TOKEN_ENDPOINT", None)
        self.custom_api_client_id = getattr(settings, "AUTH0_CUSTOM_API_CLIENT_ID", None)
        self.custom_api_client_secret = getattr(settings, "AUTH0_CUSTOM_API_CLIENT_SECRET", None)

        self.slack_connection_name = getattr(
            settings,
            "AUTH0_SLACK_CONNECTION_NAME",
            "sign-in-with-slack",
        )
        self.google_connection_name = getattr(
            settings,
            "AUTH0_GOOGLE_CONNECTION_NAME",
            "google-oauth2",
        )
        self.github_connection_name = getattr(
            settings,
            "AUTH0_GITHUB_CONNECTION_NAME",
            "github",
        )

        if not self.auth0_token_endpoint and self.auth0_domain:
            self.auth0_token_endpoint = f"https://{self.auth0_domain}/oauth/token"

    @property
    def is_configured(self) -> bool:
        return all(
            [
                self.auth0_token_endpoint,
                self.custom_api_client_id,
                self.custom_api_client_secret,
                self.slack_connection_name,
                self.google_connection_name,
                self.github_connection_name,
            ]
        )

    def get_provider_token(
        self,
        provider: str,
        scopes: list[str],
        user_access_token: str | None = None,
        user_id: str | None = None,
        actor_email: str | None = None,
        reason: str = "",
        incident_id: str | None = None,
    ) -> dict[str, Any]:
        normalized = self._normalize_provider(provider)

        if normalized in self.SYSTEM_OWNED_PROVIDERS:
            logger.info(
                "[TOKEN VAULT] provider=%s is system-owned, no exchange performed",
                normalized,
            )
            return {
                "success": True,
                "mode": "system-owned",
                "provider": normalized,
                "connection": None,
                "access_token": None,
                "expires_in": None,
                "scopes": [],
                "reason": reason,
                "incident_id": incident_id,
                "user_id": user_id,
                "actor_email": actor_email,
            }

        if normalized not in self.VAULT_BACKED_PROVIDERS:
            return {
                "success": False,
                "provider": normalized,
                "error": f"Unsupported provider for Token Vault exchange: {normalized}",
            }

        if not self.is_configured:
            return {
                "success": False,
                "provider": normalized,
                "error": (
                    "Token Vault adapter is not fully configured. "
                    "Missing one or more of AUTH0_TOKEN_ENDPOINT, "
                    "AUTH0_CUSTOM_API_CLIENT_ID, AUTH0_CUSTOM_API_CLIENT_SECRET, "
                    "AUTH0_SLACK_CONNECTION_NAME, AUTH0_GOOGLE_CONNECTION_NAME, "
                    "AUTH0_GITHUB_CONNECTION_NAME."
                ),
            }

        if not user_access_token:
            return {
                "success": False,
                "provider": normalized,
                "error": "Missing Auth0 operator access token for Token Vault exchange",
            }

        connection = self._get_connection_name(normalized)
        requested_scopes = self._normalize_requested_scopes(normalized, scopes)

        payload: dict[str, Any] = {
            "client_id": self.custom_api_client_id,
            "client_secret": self.custom_api_client_secret,
            "grant_type": self.TOKEN_EXCHANGE_GRANT,
            "subject_token": user_access_token,
            "subject_token_type": self.SUBJECT_TOKEN_TYPE,
            "requested_token_type": self.REQUESTED_TOKEN_TYPE,
            "connection": connection,
        }

        # For GitHub, Auth0's current integration docs note dynamic scopes are not supported,
        # so only include scope when we actually have a non-empty normalized scope list.
        if requested_scopes:
            payload["scope"] = " ".join(requested_scopes)

        logger.info(
            "[TOKEN VAULT] exchange start provider=%s connection=%s scopes=%s incident_id=%s actor_email=%s user_id=%s subject_principal=%s",
            normalized,
            connection,
            requested_scopes,
            incident_id,
            actor_email,
            user_id,
            user_id or actor_email,
        )

        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(
                    self.auth0_token_endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

            if response.status_code >= 400:
                logger.error(
                    "[TOKEN VAULT] exchange failed provider=%s connection=%s status=%s body=%s",
                    normalized,
                    connection,
                    response.status_code,
                    response.text[:1000],
                )
                return {
                    "success": False,
                    "provider": normalized,
                    "connection": connection,
                    "status_code": response.status_code,
                    "error": response.text,
                    "requested_scopes": requested_scopes,
                }

            data = response.json()
            access_token = data.get("access_token")

            if not access_token:
                logger.error(
                    "[TOKEN VAULT] exchange returned no access_token provider=%s connection=%s body=%s",
                    normalized,
                    connection,
                    data,
                )
                return {
                    "success": False,
                    "provider": normalized,
                    "connection": connection,
                    "error": "Token exchange succeeded but no access_token was returned",
                    "raw": data,
                }

            returned_scope_string = data.get("scope", "")
            returned_scopes = (
                returned_scope_string.split()
                if isinstance(returned_scope_string, str) and returned_scope_string
                else requested_scopes
            )

            logger.info(
                "[TOKEN VAULT] exchange success provider=%s connection=%s expires_in=%s scopes=%s user_id=%s actor_email=%s",
                normalized,
                connection,
                data.get("expires_in"),
                returned_scopes,
                user_id,
                actor_email,
            )

            return {
                "success": True,
                "mode": "auth0-token-vault",
                "provider": normalized,
                "connection": connection,
                "access_token": access_token,
                "token_type": data.get("token_type", "Bearer"),
                "issued_token_type": data.get("issued_token_type"),
                "expires_in": data.get("expires_in"),
                "scopes": returned_scopes,
                "requested_scopes": requested_scopes,
                "incident_id": incident_id,
                "user_id": user_id,
                "actor_email": actor_email,
                "reason": reason,
            }

        except Exception as exc:
            logger.exception(
                "[TOKEN VAULT] exchange exception provider=%s connection=%s",
                normalized,
                connection,
            )
            return {
                "success": False,
                "provider": normalized,
                "connection": connection,
                "error": str(exc),
                "requested_scopes": requested_scopes,
            }

    def revoke_provider_token(self, provider: str, user_id: str | None = None) -> dict[str, Any]:
        normalized = self._normalize_provider(provider)
        return {
            "success": False,
            "provider": normalized,
            "user_id": user_id,
            "error": "Provider token revocation is not implemented in this adapter yet",
        }

    def check_connection_status(self, provider: str, user_id: str | None = None) -> dict[str, Any]:
        normalized = self._normalize_provider(provider)
        connection = self._get_connection_name(normalized) if normalized in self.VAULT_BACKED_PROVIDERS else None

        return {
            "connected": normalized in self.SYSTEM_OWNED_PROVIDERS or self.is_configured,
            "provider": normalized,
            "connection": connection,
            "mode": "system-owned" if normalized in self.SYSTEM_OWNED_PROVIDERS else "auth0-token-vault",
            "user_id": user_id,
        }

    def build_authorization_details(
        self,
        provider: str,
        scopes: list[str],
        incident_id: str,
        action_type: str,
        recipients: list[str] | None = None,
        risk_level: str | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        normalized = self._normalize_provider(provider)
        requested_scopes = self._normalize_requested_scopes(normalized, scopes)

        return {
            "type": "incident-action-approval",
            "provider": normalized,
            "incident_id": incident_id,
            "action_type": action_type,
            "scopes": requested_scopes,
            "recipients": recipients or [],
            "risk_level": risk_level,
            "reason": reason,
        }

    def _get_connection_name(self, normalized_provider: str) -> str:
        if normalized_provider == "google":
            return self.google_connection_name
        if normalized_provider == "slack":
            return self.slack_connection_name
        if normalized_provider == "github":
            return self.github_connection_name
        return normalized_provider

    def _normalize_requested_scopes(self, provider: str, scopes: list[str]) -> list[str]:
        cleaned = [str(s).strip() for s in (scopes or []) if str(s).strip()]
        if not cleaned:
            return []

        mapping = {}
        if provider == "google":
            mapping = self.GOOGLE_SCOPE_MAP
        elif provider == "slack":
            mapping = self.SLACK_SCOPE_MAP
        elif provider == "github":
            # Auth0's current GitHub AI integration docs note dynamic scopes are not supported.
            # Return an empty list so we do not send scope in the exchange payload for GitHub.
            return []

        normalized: list[str] = []
        seen: set[str] = set()

        for scope in cleaned:
            mapped = mapping.get(scope, scope)

            if mapped not in seen:
                seen.add(mapped)
                normalized.append(mapped)

        return normalized

    def _normalize_provider(self, provider: str) -> str:
        p = (provider or "").strip().lower()

        if p in {"google", "google calendar", "google-oauth2"}:
            return "google"
        if p in {"slack", "sign-in-with-slack", "slack-oauth2"}:
            return "slack"
        if p in {"github"}:
            return "github"
        if p in {"zoom"}:
            return "zoom"
        if p in {"smtp", "email", "email (smtp)"}:
            return "smtp"

        return p
