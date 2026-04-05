import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Explicitly load backend/.env so these values are available even if the
# process environment was not populated the way we expect.
BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")

TEST_EMAIL_RECIPIENTS = [
    "ray.garg@zappsec.com",
    "hitesh.kumar@zappsec.com",
    "devender.singh@zappsec.com",
]

# Replace these with the REAL Slack member IDs for Ray / Hitesh / Devender.
TEST_SLACK_RECIPIENTS = [
    "U0APAFNJ4TX",
    "U0APHFKNL5S",
    "U0APAFRE8RK",
]

DEMO_CALENDAR_ID = "a064052cbc78517915596d76e0a9a375f407f93dbaaff8ae1f9e8285b8bbb55d@group.calendar.google.com"

CONFIG_DRIFT_KEYWORDS = [
    "port 81",
    "port 80",
    "config drift",
    "network policy",
    "firewall rule",
    "security group",
    "ingress rule",
    "service now listens on port 81",
    "policy still permits only 80",
]


def _github_targets() -> dict:
    """
    Resolve GitHub remediation targets from the current environment.
    """
    app_repo = os.getenv(
        "GITHUB_APP_REMEDIATION_REPO",
        "RayGarg-Zapp/warroom-app-remediation",
    )
    app_path = os.getenv(
        "GITHUB_APP_REMEDIATION_PATH",
        "service-config.json",
    )
    network_repo = os.getenv(
        "GITHUB_NETWORK_REMEDIATION_REPO",
        "RayGarg-Zapp/warroom-network-remediation",
    )
    network_path = os.getenv(
        "GITHUB_NETWORK_REMEDIATION_PATH",
        "network-policy.json",
    )

    return {
        "app_repo": app_repo,
        "app_path": app_path,
        "network_repo": network_repo,
        "network_path": network_path,
    }


def _is_config_drift_incident(title: str, summary: str, known_issues: list[dict]) -> bool:
    corpus_parts = [title or "", summary or ""]

    for issue in known_issues or []:
        corpus_parts.append(issue.get("title", ""))
        corpus_parts.append(issue.get("description", ""))
        corpus_parts.append(issue.get("rootCauseSummary", ""))

    text = " ".join(corpus_parts).lower()
    return any(keyword in text for keyword in CONFIG_DRIFT_KEYWORDS)


def _build_app_service_config(incident_id: str, reason: str) -> dict:
    """
    Production-shaped application service configuration artifact.
    Only the listen_port is changed by remediation.
    """
    return {
        "metadata": {
            "service_name": "customer-portal",
            "application_id": "cust-portal-prod",
            "environment": "prod",
            "cloud": "azure",
            "platform": "aks",
            "managed_by": "terraform",
            "config_version": "2026.04.01",
            "owner_team": "cloud-platform",
            "support_contact": "cloud-platform@company.example",
        },
        "deployment": {
            "region": "eastus2",
            "resource_group": "rg-prod-customer-portal",
            "subscription_alias": "prod-shared-platform",
            "aks_cluster": "aks-prod-eastus2-01",
            "namespace": "customer-portal",
            "node_pool": "systempool01",
            "container_image": "acrprod001.azurecr.io/customer-portal:2026.03.31.7",
            "replicas": {
                "min": 3,
                "desired": 6,
                "max": 12,
            },
        },
        "service": {
            "service_type": "ClusterIP",
            "listen_port": 81,
            "target_port": 8080,
            "protocol": "TCP",
            "public_hostname": "portal.company.example",
            "ingress_controller": "azure-application-gateway",
        },
        "identity": {
            "entra_application": "entra-app-customer-portal-prod",
            "managed_identity": "mi-customer-portal-prod",
            "key_vault": "kv-prod-customer-portal-01",
        },
        "observability": {
            "log_analytics_workspace": "law-prod-shared-01",
            "app_insights": "appi-customer-portal-prod",
            "diagnostic_setting": "diag-customer-portal-prod",
        },
        "policy_controls": {
            "azure_policy_initiative": "prod-kubernetes-security-baseline",
            "defender_for_cloud": True,
            "image_signing_required": True,
            "private_ingress_only": False,
        },
        "change_context": {
            "incident_id": incident_id,
            "updated_by": "warroom-agent",
            "reason": reason,
        },
    }


def _build_network_policy_config(incident_id: str) -> dict:
    """
    Production-shaped network policy artifact.
    Only the allowed_inbound_ports list is changed by remediation.
    """
    return {
        "metadata": {
            "policy_name": "customer-portal-ingress",
            "environment": "prod",
            "cloud": "azure",
            "managed_by": "terraform",
            "owner_team": "network-security",
            "policy_version": "2026.04.01",
            "support_contact": "network-security@company.example",
        },
        "topology": {
            "region": "eastus2",
            "hub_vnet": "vnet-prod-hub-01",
            "hub_transit": "azure-virtual-wan-eastus2",
            "spoke_vnet": "vnet-prod-app-portal-01",
            "subnet": "snet-customer-portal-app-01",
            "nsg_name": "nsg-customer-portal-ingress-01",
            "route_table": "rt-prod-app-portal-01",
            "inspection_point": "palo-alto-fw-prod-01",
        },
        "policy_subject": {
            "service_name": "customer-portal",
            "public_fqdn": "portal.company.example",
            "target_platform": "aks-prod-eastus2-01/customer-portal",
            "traffic_type": "ingress",
        },
        "ingress_policy": {
            "allowed_inbound_ports": [81],
            "protocol": "tcp",
            "source": "internet-via-app-gateway",
            "destination": "customer-portal-service",
            "action": "allow",
        },
        "security_controls": {
            "waf_policy": "waf-customer-portal-prod",
            "ddos_standard": True,
            "tls_min_version": "1.2",
            "sentinel_connector": "sentinel-prod-central",
            "flow_logs_enabled": True,
        },
        "governance": {
            "change_window": "24x7-breakfix",
            "approval_group": "netsec-sev1-approvers",
            "audit_classification": "production-network-policy",
        },
        "change_context": {
            "incident_id": incident_id,
            "updated_by": "warroom-agent",
            "reason": "Allow network policy to match the application port drift remediation",
        },
    }


def plan_actions(
    incident_id: str,
    summary: str,
    severity: str,
    title: str,
    responders: list[dict],
    known_issues: list[dict],
) -> list[dict]:
    """Generate proposed actions for incident response."""
    actions = []

    topic = f"{severity} War Room — {incident_id}: {title}"

    # 1. Zoom meeting
    actions.append({
        "action_type": "zoom_meeting",
        "title": "Create War Room",
        "description": "Open Zoom war room with the demo recipients for real-time incident coordination.",
        "risk_level": "low",
        "provider": "Zoom",
        "scopes_used": ["meeting:write"],
        "recipients": TEST_EMAIL_RECIPIENTS,
        "metadata": {
            "duration": "60",
            "topic": topic,
        },
    })

    # 2. Calendar event
    actions.append({
        "action_type": "calendar_event",
        "title": "Schedule Incident Bridge",
        "description": "Create Google Calendar event for the demo recipients with Zoom link and incident context.",
        "risk_level": "low",
        "provider": "Google Calendar",
        "scopes_used": ["calendar.events.write"],
        "recipients": TEST_EMAIL_RECIPIENTS,
        "metadata": {
            "duration": "60",
            "title": f"{severity} Incident Bridge — {title}",
            "calendar_id": DEMO_CALENDAR_ID,
        },
    })

    # 3. Slack DMs
    actions.append({
        "action_type": "slack_dm",
        "title": "Notify Responders via Slack",
        "description": "Send direct messages to the demo recipients with incident summary and war room link.",
        "risk_level": "medium",
        "provider": "Slack",
        "scopes_used": ["chat:write", "im:write"],
        "recipients": TEST_SLACK_RECIPIENTS,
        "metadata": {
            "urgency": "high" if severity == "P1" else "normal"
        },
    })

    # 4. Email notification
    if severity == "P1":
        actions.append({
            "action_type": "email_notification",
            "title": "Email Stakeholder Notification",
            "description": "Send email notification to the ZappSec demo recipients with incident briefing.",
            "risk_level": "high",
            "provider": "Email",
            "scopes_used": ["mail.send"],
            "recipients": TEST_EMAIL_RECIPIENTS,
            "metadata": {"template": "p1-executive-briefing"},
        })
    elif severity == "P2":
        actions.append({
            "action_type": "email_notification",
            "title": "Email Team Notification",
            "description": "Send email to the ZappSec demo recipients.",
            "risk_level": "medium",
            "provider": "Email",
            "scopes_used": ["mail.send"],
            "recipients": TEST_EMAIL_RECIPIENTS,
            "metadata": {"template": "p2-team-notification"},
        })

    # 5 & 6. GitHub remediation actions for config-drift incidents
    if severity == "P1" and _is_config_drift_incident(title, summary, known_issues):
        github_targets = _github_targets()

        logger.info(
            "[ACTION PLANNER] config drift targets app_repo=%s app_path=%s network_repo=%s network_path=%s incident_id=%s",
            github_targets["app_repo"],
            github_targets["app_path"],
            github_targets["network_repo"],
            github_targets["network_path"],
            incident_id,
        )

        actions.append({
            "action_type": "github_app_repo_update",
            "title": "Commit App Config Remediation",
            "description": "Update the app configuration repo so the service explicitly listens on port 81.",
            "risk_level": "high",
            "provider": "GitHub",
            "scopes_used": ["repo"],
            "recipients": ["cloud-operator"],
            "metadata": {
                "repo": github_targets["app_repo"],
                "file_path": github_targets["app_path"],
                "owner_domain": "cloud",
                "requires_individual_execution": True,
                "commit_message": f"[WarRoom] {incident_id}: align app service config to port 81",
                "desired_content": _build_app_service_config(incident_id, title),
            },
        })

        actions.append({
            "action_type": "github_network_repo_update",
            "title": "Commit Network Policy Remediation",
            "description": "Update the network policy repo so inbound traffic for the service allows port 81.",
            "risk_level": "high",
            "provider": "GitHub",
            "scopes_used": ["repo"],
            "recipients": ["network-operator"],
            "metadata": {
                "repo": github_targets["network_repo"],
                "file_path": github_targets["network_path"],
                "owner_domain": "network",
                "requires_individual_execution": True,
                "commit_message": f"[WarRoom] {incident_id}: allow inbound traffic on port 81",
                "desired_content": _build_network_policy_config(incident_id),
            },
        })

    return actions