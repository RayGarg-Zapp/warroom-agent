from __future__ import annotations

import json
import logging
from app.config import get_settings
from app.schemas.ai_outputs import IncidentClassificationOutput

logger = logging.getLogger(__name__)

# Rule-based prefilter
SEVERITY_KEYWORDS = {
    "P1": ["outage", "down", "cannot login", "cannot log in", "complete failure", "all users", "critical", "p1"],
    "P2": ["degraded", "latency", "slow", "intermittent", "some users", "p2"],
    "P3": ["minor", "cosmetic", "low impact", "p3"]
}


def _rule_based_hint(text: str) -> str | None:
    text_lower = text.lower()
    for severity, keywords in SEVERITY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return severity
    return None


def classify_incident_text(raw_message: str) -> IncidentClassificationOutput:
    """Classify incident using rule-based prefilter + Anthropic Claude LLM."""
    settings = get_settings()
    rule_hint = _rule_based_hint(raw_message)

    # Try LLM classification with Anthropic Claude
    if settings.ANTHROPIC_API_KEY:
        try:
            import anthropic
            from app.agents.prompts import INCIDENT_CLASSIFICATION_PROMPT

            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            prompt_text = INCIDENT_CLASSIFICATION_PROMPT.replace("{raw_message}", raw_message)

            response = client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt_text}
                ],
            )

            # Extract text from response
            content = ""
            for block in response.content:
                if block.type == "text":
                    content = block.text
                    break

            # Extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())
            return IncidentClassificationOutput(**data)
        except Exception as e:
            logger.warning(f"Claude LLM classification failed, using fallback: {e}")

    # Fallback: deterministic classification
    return _fallback_classify(raw_message, rule_hint)


def _fallback_classify(raw_message: str, rule_hint: str | None) -> IncidentClassificationOutput:
    """Deterministic fallback when LLM is unavailable."""
    severity = rule_hint or "P2"

    # Simple domain detection
    domain_keywords = {
        "identity": ["login", "auth", "iam", "sso", "mfa", "certificate", "saml", "oauth"],
        "network": ["cdn", "dns", "latency", "network", "firewall", "load balancer"],
        "cloud": ["aws", "azure", "gcp", "cloud", "vm", "container", "kubernetes"],
        "security": ["breach", "vulnerability", "security", "threat", "attack"],
        "application": ["api", "service", "app", "endpoint", "checkout", "portal"],
        "infrastructure": ["database", "storage", "disk", "memory", "cpu", "server"],
    }

    text_lower = raw_message.lower()
    domains = [d for d, kws in domain_keywords.items() if any(kw in text_lower for kw in kws)]
    if not domains:
        domains = ["application"]

    # Extract impacted systems from message
    systems = []
    system_keywords = {"IAM": "IAM Gateway", "SSO": "SSO Service", "MFA": "MFA Provider", "API": "API Gateway",
                       "portal": "Customer Portal", "payment": "Payment Gateway", "database": "Database Cluster",
                       "CDN": "CDN", "checkout": "Checkout Service"}
    for kw, sys_name in system_keywords.items():
        if kw.lower() in text_lower:
            systems.append(sys_name)
    if not systems:
        systems = ["Unknown System"]

    # Build summary
    confidence = 0.85 if severity == "P1" else 0.75

    return IncidentClassificationOutput(
        severity=severity,
        confidence=confidence,
        title=f"{severity} Incident — {'Critical' if severity == 'P1' else 'Elevated'} Issue Detected",
        summary=f"Automated analysis of incident report. Detected domains: {', '.join(domains)}. Impacted systems: {', '.join(systems)}.",
        severity_reasoning=f"Classified as {severity} based on keyword analysis. {'High urgency indicators found.' if severity == 'P1' else 'Moderate impact indicators.'}",
        probable_domains=domains,
        impacted_systems=systems,
    )
