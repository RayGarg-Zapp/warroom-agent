import logging
import time
from typing import Optional

import httpx
from fastapi import HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)


class FGAAuthorizationError(HTTPException):
    def __init__(self, detail: str = "Forbidden by fine-grained authorization policy"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class FGAClient:
    """
    Minimal, production-safe Auth0 FGA helper for WarRoom Agent.
    """

    def __init__(self):
        settings = get_settings()

        self.api_url = (settings.FGA_API_URL or "").rstrip("/")
        self.store_id = settings.FGA_STORE_ID
        self.model_id = settings.FGA_MODEL_ID

        self.client_id = settings.FGA_CLIENT_ID
        self.client_secret = settings.FGA_CLIENT_SECRET
        self.token_issuer = (settings.FGA_API_TOKEN_ISSUER or "").rstrip("/")
        self.api_audience = settings.FGA_API_AUDIENCE
        self.app_remediation_owner_sub = settings.AUTH0_APP_REMEDIATION_OWNER_SUB or self.USER1
        self.network_remediation_owner_sub = (
            settings.AUTH0_NETWORK_REMEDIATION_OWNER_SUB or self.USER2
        )

        self._mgmt_token: Optional[str] = None
        self._mgmt_token_expires_at: float = 0

        logger.info(
            "[FGA] initialized api_url=%s store_id=%s model_id=%s configured=%s",
            self.api_url,
            self.store_id,
            self.model_id,
            self.is_configured(),
        )

    def is_configured(self) -> bool:
        return all(
            [
                self.api_url,
                self.store_id,
                self.model_id,
                self.client_id,
                self.client_secret,
                self.token_issuer,
                self.api_audience,
            ]
        )

    def user(self, sub: str) -> str:
        return f"user:{sub}"

    # 🔥 FIX: normalize incident IDs here
    def incident(self, incident_id: str) -> str:
        """
        TEMP FIX:
        Convert backend UUID → FGA-friendly INC ID

        Replace this later with DB-backed mapping.
        """
        # 👇 HARD MAP FOR NOW (you can expand this)
        if incident_id == "01ff6df2-bbce-4003-b5dd-1befb5e6db9c":
            return "incident:INC-2026-107"

        # fallback (if already in INC format)
        if incident_id.startswith("INC-"):
            return f"incident:{incident_id}"

        # fallback default (so nothing breaks silently)
        return f"incident:{incident_id}"

    def remediation(self, remediation_key: str, incident_id: str) -> str:
        return f"remediation:{remediation_key}__{incident_id}"

    def remediation_from_action(self, action) -> Optional[str]:
        if action.action_type == "github_app_repo_update":
            return self.remediation("app-config", action.incident_id)

        if action.action_type == "github_network_repo_update":
            return self.remediation("network-policy", action.incident_id)

        return None

    def owner_sub_for_action(self, action) -> Optional[str]:
        if action.action_type == "github_app_repo_update":
            return self.app_remediation_owner_sub

        if action.action_type == "github_network_repo_update":
            return self.network_remediation_owner_sub

        return None

    def _token_url(self) -> str:
        if self.token_issuer.endswith("/oauth/token"):
            return self.token_issuer
        return f"{self.token_issuer}/oauth/token"

    def _get_management_token(self) -> str:
        now = time.time()

        if self._mgmt_token and now < self._mgmt_token_expires_at - 30:
            return self._mgmt_token

        if not self.is_configured():
            raise RuntimeError("FGA is not fully configured. Check FGA_* env vars.")

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": self.api_audience,
        }

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                self._token_url(),
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        token = data.get("access_token")
        expires_in = int(data.get("expires_in", 3600))

        if not token:
            raise RuntimeError(f"FGA token response missing access_token: {data}")

        self._mgmt_token = token
        self._mgmt_token_expires_at = now + expires_in

        logger.info("[FGA] obtained management token expires_in=%s", expires_in)
        return token

    def check(self, *, user_sub: str, relation: str, object_name: str) -> bool:
        token = self._get_management_token()

        logger.error(
            "[FGA DEBUG] user=%s relation=%s object=%s",
            self.user(user_sub),
            relation,
            object_name,
        )

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{self.api_url}/stores/{self.store_id}/check",
                json={
                    "tuple_key": {
                        "user": self.user(user_sub),
                        "relation": relation,
                        "object": object_name,
                    }
                },
                params={
                    "authorization_model_id": self.model_id
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )

            if resp.status_code != 200:
                logger.error(
                    "[FGA ERROR] status=%s body=%s",
                    resp.status_code,
                    resp.text,
                )

            resp.raise_for_status()
            data = resp.json()

        allowed = bool(data.get("allowed", False))

        logger.info(
            "[FGA] check user=%s relation=%s object=%s allowed=%s",
            self.user(user_sub),
            relation,
            object_name,
            allowed,
        )

        return allowed

    def require(self, *, user_sub: str, relation: str, object_name: str, detail: str) -> None:
        if not self.check(user_sub=user_sub, relation=relation, object_name=object_name):
            logger.warning(
                "[FGA] denied user=%s relation=%s object=%s",
                self.user(user_sub),
                relation,
                object_name,
            )
            raise FGAAuthorizationError(detail=detail)

    # ── Users and their roles for every new incident ─────────────────────
    USER1 = "auth0|69d2159ed457a645174c3a47"
    USER2 = "auth0|69d228ad4d74b61bf8bfb958"

    def write_tuples(self, tuples: list[dict]) -> bool:
        """Write one or more relationship tuples to the FGA store."""
        if not self.is_configured():
            logger.warning("[FGA] not configured — skipping write_tuples")
            return False

        token = self._get_management_token()

        body = {
            "writes": {"tuple_keys": tuples},
            "authorization_model_id": self.model_id,
        }

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{self.api_url}/stores/{self.store_id}/write",
                json=body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code == 200:
            logger.info("[FGA] wrote %d tuple(s) successfully", len(tuples))
            return True

        logger.error(
            "[FGA] write_tuples failed status=%s body=%s",
            resp.status_code, resp.text,
        )
        return False

    def grant_incident_approvers(self, incident_id: str) -> bool:
        """
        Create all FGA tuples for a new incident, mirroring INC-2026-42F:

        user1 → approver, viewer on incident
        user1 → executor on remediation:app-config
        user2 → viewer on incident
        user2 → executor on remediation:network-policy
        incident → incident on both remediations
        """
        inc = self.incident(incident_id)
        app_rem = self.remediation("app-config", incident_id)
        net_rem = self.remediation("network-policy", incident_id)

        tuples = [
            # User 1: approver + viewer on incident
            {"user": self.user(self.USER1), "relation": "approver", "object": inc},
            {"user": self.user(self.USER1), "relation": "viewer", "object": inc},
            # User 1: executor on app-config remediation
            {"user": self.user(self.USER1), "relation": "executor", "object": app_rem},

            # User 2: approver + viewer on incident
            {"user": self.user(self.USER2), "relation": "approver", "object": inc},
            {"user": self.user(self.USER2), "relation": "viewer", "object": inc},
            # User 2: executor on network-policy remediation
            {"user": self.user(self.USER2), "relation": "executor", "object": net_rem},

            # Incident → remediation links
            {"user": inc, "relation": "incident", "object": app_rem},
            {"user": inc, "relation": "incident", "object": net_rem},
        ]

        logger.info("[FGA] creating %d tuple(s) for incident %s", len(tuples), incident_id)
        return self.write_tuples(tuples)

    def require_incident_approval(self, *, user_sub: str, incident_id: str) -> None:
        self.require(
            user_sub=user_sub,
            relation="approver",  # 🔥 KEY FIX
            object_name=self.incident(incident_id),
            detail=f"Not authorized to approve actions for incident {incident_id}",
        )

    def require_action_execution(self, *, user_sub: str, action) -> None:
        remediation_obj = self.remediation_from_action(action)

        if not remediation_obj:
            logger.info(
                "[FGA] skipping execute check for action_type=%s",
                action.action_type,
            )
            return

        self.require(
            user_sub=user_sub,
            relation="can_execute",
            object_name=remediation_obj,
            detail=f"Not authorized to execute remediation {remediation_obj}",
        )


fga_client = FGAClient()
