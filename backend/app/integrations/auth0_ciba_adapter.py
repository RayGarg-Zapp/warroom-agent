from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class Auth0CIBAAdapter:
    CIBA_GRANT_TYPE = "urn:openid:params:grant-type:ciba"

    def __init__(self):
        settings = get_settings()

        self.enabled = bool(getattr(settings, "AUTH0_CIBA_ENABLED", False))
        self.domain = (getattr(settings, "AUTH0_DOMAIN", "") or "").strip()
        self.client_id = getattr(settings, "AUTH0_CIBA_CLIENT_ID", "") or getattr(
            settings,
            "AUTH0_CLIENT_ID",
            "",
        )
        self.client_secret = getattr(settings, "AUTH0_CIBA_CLIENT_SECRET", "") or getattr(
            settings,
            "AUTH0_CLIENT_SECRET",
            "",
        )
        self.audience = getattr(settings, "AUTH0_CIBA_AUDIENCE", "") or getattr(
            settings,
            "AUTH0_AUDIENCE",
            "",
        )
        self.scope = getattr(settings, "AUTH0_CIBA_SCOPE", "openid execute:remediation")
        self.requested_expiry = int(getattr(settings, "AUTH0_CIBA_REQUESTED_EXPIRY", 300) or 300)
        self.default_poll_interval = int(
            getattr(settings, "AUTH0_CIBA_DEFAULT_POLL_INTERVAL", 5) or 5
        )

        issuer = f"https://{self.domain}" if self.domain else ""
        self.bc_authorize_endpoint = f"{issuer}/bc-authorize" if issuer else ""
        self.token_endpoint = f"{issuer}/oauth/token" if issuer else ""

    @property
    def is_configured(self) -> bool:
        return bool(
            self.enabled
            and self.domain
            and self.client_id
            and self.client_secret
            and self.audience
        )

    def start_backchannel_authentication(
        self,
        *,
        user_sub: str,
        binding_message: str,
        scope: str | None = None,
        audience: str | None = None,
        requested_expiry: int | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured:
            return {
                "success": False,
                "error": "Auth0 CIBA adapter is not fully configured",
            }

        login_hint = json.dumps(
            {
                "format": "iss_sub",
                "iss": f"https://{self.domain}/",
                "sub": user_sub,
            }
        )
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "login_hint": login_hint,
            "scope": scope or self.scope,
            "audience": audience or self.audience,
            "binding_message": binding_message,
            "requested_expiry": str(requested_expiry or self.requested_expiry),
        }

        logger.info(
            "[AUTH0 CIBA] start request owner_sub=%s audience=%s scope=%s requested_expiry=%s binding_message=%s endpoint=%s",
            user_sub,
            payload["audience"],
            payload["scope"],
            payload["requested_expiry"],
            binding_message,
            self.bc_authorize_endpoint,
        )

        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(
                    self.bc_authorize_endpoint,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

            if response.status_code >= 400:
                logger.error(
                    "[AUTH0 CIBA] start failed status=%s body=%s",
                    response.status_code,
                    response.text[:1000],
                )
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text,
                }

            data = response.json()
            logger.info(
                "[AUTH0 CIBA] start accepted auth_req_id=%s expires_in=%s interval=%s owner_sub=%s",
                data.get("auth_req_id"),
                data.get("expires_in"),
                data.get("interval"),
                user_sub,
            )
            return {
                "success": True,
                "auth_req_id": data.get("auth_req_id"),
                "expires_in": int(data.get("expires_in", self.requested_expiry)),
                "interval": int(data.get("interval", self.default_poll_interval)),
            }
        except Exception as exc:
            logger.exception("[AUTH0 CIBA] start exception owner_sub=%s", user_sub)
            return {
                "success": False,
                "error": str(exc),
            }

    def poll_backchannel_authentication(self, *, auth_req_id: str) -> dict[str, Any]:
        if not self.is_configured:
            return {
                "success": False,
                "error": "Auth0 CIBA adapter is not fully configured",
            }

        payload = {
            "grant_type": self.CIBA_GRANT_TYPE,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "auth_req_id": auth_req_id,
        }

        logger.info(
            "[AUTH0 CIBA] poll request auth_req_id=%s endpoint=%s",
            auth_req_id,
            self.token_endpoint,
        )

        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(
                    self.token_endpoint,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

            data: dict[str, Any]
            try:
                data = response.json()
            except Exception:
                data = {"raw": response.text}

            if response.status_code >= 400:
                error_code = str(data.get("error") or "")
                error_description = str(data.get("error_description") or response.text)
                interval = int(data.get("interval", self.default_poll_interval))
                pending = error_code in {"authorization_pending", "slow_down"}
                terminal = error_code in {"access_denied", "expired_token"}

                logger.warning(
                    "[AUTH0 CIBA] poll non-success auth_req_id=%s status=%s error=%s description=%s interval=%s",
                    auth_req_id,
                    response.status_code,
                    error_code,
                    error_description,
                    interval,
                )
                return {
                    "success": False,
                    "pending": pending,
                    "terminal": terminal,
                    "error": error_code or "ciba_poll_failed",
                    "error_description": error_description,
                    "interval": interval,
                    "status_code": response.status_code,
                }

            logger.info(
                "[AUTH0 CIBA] poll approved auth_req_id=%s expires_in=%s scope=%s token_type=%s",
                auth_req_id,
                data.get("expires_in"),
                data.get("scope"),
                data.get("token_type"),
            )
            return {
                "success": True,
                "pending": False,
                "terminal": True,
                "access_token": data.get("access_token"),
                "scope": data.get("scope"),
                "expires_in": data.get("expires_in"),
                "token_type": data.get("token_type"),
            }
        except Exception as exc:
            logger.exception("[AUTH0 CIBA] poll exception auth_req_id=%s", auth_req_id)
            return {
                "success": False,
                "pending": False,
                "terminal": False,
                "error": "ciba_poll_exception",
                "error_description": str(exc),
                "interval": self.default_poll_interval,
            }
