"""
Execution Guard — Security layer that verifies actions are safe to execute.

Trust boundaries:
- AI reasoning layer can propose any action
- Execution guard validates before any external call
- High-risk actions require explicit approval
- Step-up flags trigger additional verification
"""
import json
import logging

logger = logging.getLogger(__name__)

class ExecutionGuard:
    """Validates that an action is safe to execute."""

    STEP_UP_TRIGGERS = {
        "executive_recipients": ["cto", "ceo", "vp-", "chief", "president"],
        "external_domains": ["gmail.com", "yahoo.com", "hotmail.com"],
        "high_recipient_count": 10,
    }

    def can_execute(self, action) -> bool:
        """Check if an action can be executed."""
        # Must be approved
        if action.approval_required and action.approval_status != "approved":
            logger.warning(f"Action {action.id} requires approval but status is {action.approval_status}")
            return False

        # Must not already be executed
        if action.execution_status in ("executed", "executing"):
            logger.warning(f"Action {action.id} already {action.execution_status}")
            return False

        # Check step-up triggers
        if self._needs_step_up(action):
            logger.info(f"Action {action.id} triggered step-up verification")
            # In MVP, we log but don't block — step-up auth is a future enhancement
            # TODO: Integrate with Auth0 step-up authentication

        return True

    def _needs_step_up(self, action) -> bool:
        """Check if action triggers step-up authentication."""
        recipients_json = action.recipients_json if hasattr(action, 'recipients_json') else "[]"
        try:
            recipients = json.loads(recipients_json) if isinstance(recipients_json, str) else []
        except:
            recipients = []

        # Check executive recipients
        for r in recipients:
            r_lower = r.lower()
            if any(trigger in r_lower for trigger in self.STEP_UP_TRIGGERS["executive_recipients"]):
                return True

        # Check external domains
        for r in recipients:
            if "@" in r:
                domain = r.split("@")[1].lower()
                if domain in self.STEP_UP_TRIGGERS["external_domains"]:
                    return True

        # Check recipient count
        if len(recipients) >= self.STEP_UP_TRIGGERS["high_recipient_count"]:
            return True

        return False

    def get_risk_assessment(self, action) -> dict:
        """Get risk assessment for an action."""
        needs_step_up = self._needs_step_up(action)
        return {
            "action_id": action.id,
            "risk_level": action.risk_level,
            "approval_required": action.approval_required,
            "step_up_required": needs_step_up,
            "can_execute": self.can_execute(action),
        }
