from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
import uuid

from app.database import SessionLocal
from app.models.audit_entry import AuditEntry
from app.models.incident import Incident
from app.models.planned_action import PlannedAction
from app.security.execution_guard import ExecutionGuard
from app.integrations.token_vault_adapter import TokenVaultAdapter

logger = logging.getLogger(__name__)

ACTION_ORDER = {
    "zoom_meeting": 1,
    "calendar_event": 2,
    "slack_dm": 3,
    "email_notification": 4,
    "github_app_repo_update": 5,
    "github_network_repo_update": 6,
}

VAULT_PROVIDER_MAP = {
    "calendar_event": "google",
    "slack_dm": "slack",
    "github_app_repo_update": "github",
    "github_network_repo_update": "github",
}

VAULT_SCOPE_MAP = {
    "calendar_event": ["calendar.events"],
    "slack_dm": ["chat:write", "im:write"],
    # GitHub dynamic scopes are not passed through Token Vault in this integration path.
    "github_app_repo_update": [],
    "github_network_repo_update": [],
}

SENSITIVE_INDIVIDUAL_ACTIONS = {
    "github_app_repo_update",
    "github_network_repo_update",
}


def _load_metadata(action: PlannedAction) -> dict:
    raw = action.metadata_json or "{}"
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _save_metadata(action: PlannedAction, metadata: dict) -> None:
    action.metadata_json = json.dumps(metadata)


def execute_approved_actions(incident_id: str, operator_context: dict | None = None) -> list[dict]:
    """
    Execute all approved actions for an incident.

    Sensitive GitHub remediation actions are intentionally skipped here so they
    must be executed individually by the correct operator. This preserves the
    demo shape where the wrong operator can fail and the right operator can succeed.
    """
    db = SessionLocal()
    results = []
    context = {}
    operator_context = operator_context or {}
    token_vault = TokenVaultAdapter()

    try:
        actions = db.query(PlannedAction).filter(
            PlannedAction.incident_id == incident_id,
            PlannedAction.approval_status == "approved",
            PlannedAction.execution_status == "pending"
        ).all()

        actions = sorted(
            actions,
            key=lambda a: (
                ACTION_ORDER.get(a.action_type, 99),
                a.created_at or datetime.now(timezone.utc)
            )
        )

        guard = ExecutionGuard()

        for action in actions:
            try:
                if action.action_type in SENSITIVE_INDIVIDUAL_ACTIONS:
                    results.append({
                        "action_id": action.id,
                        "status": "requires_individual_execution",
                        "reason": "Sensitive GitHub remediation actions must be executed individually by the correct operator",
                        "token_path": "token-vault",
                        "vault_provider": "github",
                        "vault_mode": "auth0-token-vault",
                    })

                    audit = AuditEntry(
                        id=str(uuid.uuid4()),
                        incident_id=incident_id,
                        action_id=action.id,
                        actor_type="system",
                        actor_name="WarRoom Agent",
                        event_name=f"Action deferred for individual execution: {action.title}",
                        target_system=action.provider or action.target_system or "",
                        execution_status="pending",
                        details_json=json.dumps({
                            "operator_sub": operator_context.get("sub"),
                            "operator_email": operator_context.get("email"),
                            "reason": "Sensitive remediation action was intentionally skipped during bulk execution",
                        }),
                        timestamp=datetime.now(timezone.utc),
                    )
                    db.add(audit)
                    db.commit()
                    continue

                if not guard.can_execute(action):
                    logger.warning("Execution blocked by guard: %s", action.id)
                    results.append({
                        "action_id": action.id,
                        "status": "blocked",
                        "reason": "execution guard",
                    })
                    continue

                if context.get("zoom_join_url") and action.action_type in {"calendar_event", "slack_dm", "email_notification"}:
                    metadata = _load_metadata(action)
                    metadata["zoom_join_url"] = context["zoom_join_url"]
                    _save_metadata(action, metadata)
                    db.commit()

                action.execution_status = "executing"
                db.commit()

                result = _execute_single_action(
                    action,
                    operator_context=operator_context,
                    token_vault=token_vault,
                )

                if action.action_type == "zoom_meeting" and result.get("success") and result.get("join_url"):
                    context["zoom_join_url"] = result["join_url"]

                action.execution_status = "executed" if result.get("success") else "failed"
                action.executed_at = datetime.now(timezone.utc)

                audit = AuditEntry(
                    id=str(uuid.uuid4()),
                    incident_id=incident_id,
                    action_id=action.id,
                    actor_type="system",
                    actor_name="WarRoom Agent",
                    event_name=f"Action {'executed' if result.get('success') else 'failed'}: {action.title}",
                    target_system=action.provider or action.target_system or "",
                    execution_status=action.execution_status,
                    details_json=json.dumps({
                        "operator_sub": operator_context.get("sub"),
                        "operator_email": operator_context.get("email"),
                        "token_path": result.get("token_path"),
                        "vault_provider": result.get("vault_provider"),
                        "vault_mode": result.get("vault_mode"),
                        "provider_result": result,
                    }),
                    timestamp=datetime.now(timezone.utc),
                )
                db.add(audit)
                db.commit()

                results.append({
                    "action_id": action.id,
                    "status": action.execution_status,
                    **result,
                })

            except Exception as e:
                logger.error("Action execution failed: %s: %s", action.id, e)
                action.execution_status = "failed"
                db.commit()
                results.append({
                    "action_id": action.id,
                    "status": "failed",
                    "error": str(e),
                })

        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if incident:
            all_done = all(
                r["status"] in ("executed", "blocked", "requires_individual_execution")
                for r in results
            )
            incident.status = "in_progress" if all_done else "failed"
            db.commit()

        return results
    finally:
        db.close()


def _execute_single_action(
    action: PlannedAction,
    operator_context: dict | None = None,
    token_vault: TokenVaultAdapter | None = None,
) -> dict:
    """
    Route action to the appropriate integration adapter.

    For vault-backed providers:
    - retrieve a provider token first
    - pass it directly to the adapter
    - never persist raw token
    """
    operator_context = operator_context or {}
    token_vault = token_vault or TokenVaultAdapter()
    action_type = action.action_type

    provider_result = {
        "success": True,
        "mode": "system-owned",
        "provider": None,
        "access_token": None,
        "scopes": [],
    }

    if action_type in VAULT_PROVIDER_MAP:
        provider = VAULT_PROVIDER_MAP[action_type]
        scopes = VAULT_SCOPE_MAP.get(action_type, [])
        recipients = json.loads(action.recipients_json) if action.recipients_json else []

        provider_result = token_vault.get_provider_token(
            provider=provider,
            scopes=scopes,
            user_access_token=operator_context.get("auth0_access_token"),
            user_id=operator_context.get("sub"),
            actor_email=operator_context.get("email"),
            incident_id=action.incident_id,
            reason=f"{action.title} for incident {action.incident_id}",
        )

        if not provider_result.get("success"):
            return {
                "success": False,
                "error": provider_result.get("error", "Token Vault retrieval failed"),
                "token_path": "token-vault",
                "vault_provider": provider,
                "vault_mode": provider_result.get("mode"),
                "authorization_details": token_vault.build_authorization_details(
                    provider=provider,
                    scopes=scopes,
                    incident_id=action.incident_id,
                    action_type=action.action_type,
                    recipients=recipients,
                    risk_level=action.risk_level,
                    reason=f"{action.title} for incident {action.incident_id}",
                ),
            }

    if action_type == "zoom_meeting":
        from app.integrations.zoom_adapter import ZoomAdapter
        adapter = ZoomAdapter()
        result = adapter.create_meeting(action)
        result["token_path"] = "system-owned"
        result["vault_provider"] = None
        result["vault_mode"] = "system-owned"
        return result

    if action_type == "calendar_event":
        from app.integrations.google_calendar_adapter import GoogleCalendarAdapter
        adapter = GoogleCalendarAdapter()
        result = adapter.create_event(
            action,
            access_token=provider_result.get("access_token"),
            token_context=provider_result,
        )
        result["token_path"] = "token-vault"
        result["vault_provider"] = "google"
        result["vault_mode"] = provider_result.get("mode")
        result["authorization_details"] = token_vault.build_authorization_details(
            provider="google",
            scopes=VAULT_SCOPE_MAP["calendar_event"],
            incident_id=action.incident_id,
            action_type=action.action_type,
            recipients=json.loads(action.recipients_json) if action.recipients_json else [],
            risk_level=action.risk_level,
            reason=f"{action.title} for incident {action.incident_id}",
        )
        return result

    if action_type == "slack_dm":
        from app.integrations.slack_adapter import SlackAdapter
        adapter = SlackAdapter()
        result = adapter.send_dm(
            action,
            access_token=provider_result.get("access_token"),
            token_context=provider_result,
        )
        result["token_path"] = "token-vault"
        result["vault_provider"] = "slack"
        result["vault_mode"] = provider_result.get("mode")
        result["authorization_details"] = token_vault.build_authorization_details(
            provider="slack",
            scopes=VAULT_SCOPE_MAP["slack_dm"],
            incident_id=action.incident_id,
            action_type=action.action_type,
            recipients=json.loads(action.recipients_json) if action.recipients_json else [],
            risk_level=action.risk_level,
            reason=f"{action.title} for incident {action.incident_id}",
        )
        return result

    if action_type in {"github_app_repo_update", "github_network_repo_update"}:
        from app.integrations.github_adapter import GitHubAdapter
        adapter = GitHubAdapter()
        result = adapter.update_file(
            action,
            access_token=provider_result.get("access_token"),
            token_context=provider_result,
        )
        result["token_path"] = "token-vault"
        result["vault_provider"] = "github"
        result["vault_mode"] = provider_result.get("mode")
        result["authorization_details"] = token_vault.build_authorization_details(
            provider="github",
            scopes=[],
            incident_id=action.incident_id,
            action_type=action.action_type,
            recipients=json.loads(action.recipients_json) if action.recipients_json else [],
            risk_level=action.risk_level,
            reason=f"{action.title} for incident {action.incident_id}",
        )
        return result

    if action_type == "email_notification":
        from app.integrations.email_adapter import EmailAdapter
        adapter = EmailAdapter()
        result = adapter.send_email(action)
        result["token_path"] = "system-owned"
        result["vault_provider"] = None
        result["vault_mode"] = "system-owned"
        return result

    return {"success": False, "error": f"Unknown action type: {action_type}"}