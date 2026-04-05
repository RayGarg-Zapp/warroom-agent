"""
WarRoom Agent — LangGraph Node Functions

Each function receives the full IncidentWorkflowState and returns a *partial*
dict that LangGraph merges back into state.  The Annotated[list, add] fields
(like audit_entries) are appended automatically.

All heavy lifting is delegated to service modules under app.services.
"""

from datetime import datetime, timezone

from app.agents.state import IncidentWorkflowState


def _ts() -> str:
    """ISO-8601 UTC timestamp helper."""
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# 1. Ingest
# --------------------------------------------------------------------------- #
def ingest_event(state: IncidentWorkflowState) -> dict:
    """Store raw incident and set stage."""
    import json
    source = state.get("source", "unknown")
    raw = state.get("raw_message", "")
    return {
        "current_stage": "classifying",
        "audit_entries": [
            {
                "event": f"Incident ingested from {source}",
                "actor_type": "system",
                "actor_name": "Slack Poller",
                "target_system": source,
                "timestamp": _ts(),
                "details_json": json.dumps({
                    "stage": "ingest",
                    "raw_message": raw[:500],
                    "source_channel": source,
                    "description": "Raw incident message received and queued for AI classification.",
                }),
            }
        ],
    }


# --------------------------------------------------------------------------- #
# 2. Classify
# --------------------------------------------------------------------------- #
def classify_incident(state: IncidentWorkflowState) -> dict:
    """Use LLM to classify severity, domains, and impacted systems."""
    from app.services.incident_classifier import classify_incident_text

    result = classify_incident_text(state["raw_message"])

    import json
    return {
        "severity": result.severity,
        "confidence": result.confidence,
        "title": result.title,
        "summary": result.summary,
        "severity_reasoning": result.severity_reasoning,
        "probable_domains": result.probable_domains,
        "impacted_systems": result.impacted_systems,
        "current_stage": "resolving_responders",
        "audit_entries": [
            {
                "event": (
                    f"AI classified incident as {result.severity} "
                    f"(confidence: {result.confidence:.0%}) — \"{result.title}\""
                ),
                "actor_type": "ai_agent",
                "actor_name": "Classification Agent",
                "target_system": "Anthropic Claude",
                "timestamp": _ts(),
                "details_json": json.dumps({
                    "stage": "classify",
                    "severity": result.severity,
                    "confidence": result.confidence,
                    "title": result.title,
                    "summary": result.summary,
                    "severity_reasoning": result.severity_reasoning,
                    "probable_domains": result.probable_domains,
                    "impacted_systems": result.impacted_systems,
                    "description": f"AI analysed the raw message and determined this is a {result.severity} incident. {result.severity_reasoning}",
                }),
            }
        ],
    }


# --------------------------------------------------------------------------- #
# 3. Resolve responders
# --------------------------------------------------------------------------- #
def resolve_responders(state: IncidentWorkflowState) -> dict:
    """Find appropriate responders for this incident."""
    from app.services.responder_resolver import resolve_responders as _resolve

    responders = _resolve(
        summary=state.get("summary", ""),
        severity=state.get("severity", "P2"),
        domains=state.get("probable_domains", []),
    )

    import json
    unique_domains = len({r.get("domain", "") for r in responders})
    responder_names = [r.get("name", "?") for r in responders]

    return {
        "responders": responders,
        "current_stage": "matching_known_issues",
        "audit_entries": [
            {
                "event": (
                    f"{len(responders)} responders identified "
                    f"across {unique_domains} domain(s): {', '.join(responder_names)}"
                ),
                "actor_type": "ai_agent",
                "actor_name": "Responder Agent",
                "target_system": "Responder Directory",
                "timestamp": _ts(),
                "details_json": json.dumps({
                    "stage": "resolve_responders",
                    "responder_count": len(responders),
                    "domain_count": unique_domains,
                    "responders": [
                        {
                            "name": r.get("name"),
                            "role": r.get("role"),
                            "domain": r.get("domain"),
                            "confidence": r.get("confidence"),
                            "reason": r.get("reason", ""),
                        }
                        for r in responders
                    ],
                    "description": f"AI selected {len(responders)} on-call responders based on incident domains and expertise match.",
                }),
            }
        ],
    }


# --------------------------------------------------------------------------- #
# 4. Known-issue lookup
# --------------------------------------------------------------------------- #
def lookup_known_issues(state: IncidentWorkflowState) -> dict:
    """Search knowledge base for matching known issues."""
    from app.services.known_issue_engine import match_known_issues

    matches = match_known_issues(
        summary=state.get("summary", ""),
        severity=state.get("severity", "P2"),
        domains=state.get("probable_domains", []),
    )

    import json
    match_titles = [m.get("title", "?") for m in matches]

    return {
        "known_issues": matches,
        "current_stage": "planning_actions",
        "audit_entries": [
            {
                "event": (
                    f"{len(matches)} known issue(s) matched"
                    + (f": {', '.join(match_titles)}" if match_titles else "")
                ),
                "actor_type": "ai_agent",
                "actor_name": "Knowledge Base Agent",
                "target_system": "Known Issues DB",
                "timestamp": _ts(),
                "details_json": json.dumps({
                    "stage": "known_issue_match",
                    "match_count": len(matches),
                    "matches": [
                        {
                            "title": m.get("title"),
                            "match_score": m.get("match_score") or m.get("matchScore"),
                            "matched_symptoms": m.get("matched_symptoms", []),
                            "recommended_actions": m.get("recommended_actions", []),
                        }
                        for m in matches
                    ],
                    "description": f"Searched knowledge base and found {len(matches)} historical issue(s) with similar symptoms.",
                }),
            }
        ],
    }


# --------------------------------------------------------------------------- #
# 5. Plan actions
# --------------------------------------------------------------------------- #
def plan_actions(state: IncidentWorkflowState) -> dict:
    """Generate an action plan for the incident."""
    from app.services.action_planner import plan_actions as _plan

    actions = _plan(
        incident_id=state["incident_id"],
        summary=state.get("summary", ""),
        severity=state.get("severity", "P2"),
        title=state.get("title", ""),
        responders=state.get("responders", []),
        known_issues=state.get("known_issues", []),
    )

    import json
    has_high_risk = any(
        a.get("risk_level") in ("high", "critical") for a in actions
    )

    status_label = "awaiting approval" if has_high_risk else "auto-approved"

    return {
        "proposed_actions": actions,
        "approvals_required": has_high_risk,
        "current_stage": "awaiting_approval" if has_high_risk else "executing",
        "audit_entries": [
            {
                "event": f"{len(actions)} action(s) proposed — {status_label}",
                "actor_type": "ai_agent",
                "actor_name": "Action Planner Agent",
                "target_system": "Action Engine",
                "timestamp": _ts(),
                "details_json": json.dumps({
                    "stage": "plan_actions",
                    "action_count": len(actions),
                    "requires_approval": has_high_risk,
                    "actions": [
                        {
                            "title": a.get("title"),
                            "action_type": a.get("action_type"),
                            "risk_level": a.get("risk_level"),
                            "description": a.get("description", ""),
                            "recipients": a.get("recipients", []),
                            "provider": a.get("provider", ""),
                        }
                        for a in actions
                    ],
                    "description": f"AI proposed {len(actions)} action(s). "
                        + ("High/critical risk actions require human approval." if has_high_risk else "All actions auto-approved (low/medium risk)."),
                }),
            }
        ],
    }


# --------------------------------------------------------------------------- #
# 6. Approval gate  (conditional edge — returns a routing string, not state)
# --------------------------------------------------------------------------- #
def check_approval(state: IncidentWorkflowState) -> str:
    """Conditional edge: returns 'wait' if human approval is still pending,
    otherwise 'execute' to proceed with action execution."""
    if state.get("approvals_required", False) and not state.get(
        "all_approved", False
    ):
        return "wait"
    return "execute"


# --------------------------------------------------------------------------- #
# 7. Execute actions
# --------------------------------------------------------------------------- #
def execute_actions(state: IncidentWorkflowState) -> dict:
    """Execute approved actions through integration adapters."""
    from app.services.execution_engine import execute_approved_actions

    results = execute_approved_actions(state["incident_id"])

    import json
    succeeded = sum(1 for r in results if r.get("success"))
    failed = len(results) - succeeded

    return {
        "execution_results": results,
        "current_stage": "finalized",
        "audit_entries": [
            {
                "event": f"Execution complete — {succeeded} succeeded, {failed} failed out of {len(results)}",
                "actor_type": "system",
                "actor_name": "Execution Engine",
                "target_system": "Integration Layer",
                "timestamp": _ts(),
                "details_json": json.dumps({
                    "stage": "execute",
                    "total": len(results),
                    "succeeded": succeeded,
                    "failed": failed,
                    "results": results[:10],  # cap to avoid huge payloads
                    "description": f"Executed {len(results)} approved action(s) via integration adapters.",
                }),
            }
        ],
    }


# --------------------------------------------------------------------------- #
# 8. Finalize
# --------------------------------------------------------------------------- #
def finalize_incident(state: IncidentWorkflowState) -> dict:
    """Mark the incident workflow as complete."""
    import json
    return {
        "current_stage": "completed",
        "audit_entries": [
            {
                "event": "Incident workflow finalized — all stages complete",
                "actor_type": "system",
                "actor_name": "Workflow Engine",
                "target_system": "WarRoom Agent",
                "timestamp": _ts(),
                "details_json": json.dumps({
                    "stage": "finalize",
                    "incident_id": state.get("incident_id"),
                    "final_severity": state.get("severity"),
                    "final_title": state.get("title"),
                    "responder_count": len(state.get("responders") or []),
                    "action_count": len(state.get("proposed_actions") or []),
                    "description": "All workflow stages completed. Incident is now in the hands of the on-call team.",
                }),
            }
        ],
    }
