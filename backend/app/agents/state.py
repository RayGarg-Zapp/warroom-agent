"""
WarRoom Agent — LangGraph Workflow State

Defines the shared state schema that flows through every node in the
incident-response graph.  Uses LangGraph's Annotated[list, add] pattern
so that audit_entries from each node are *appended* rather than replaced.
"""

from typing import TypedDict, Optional, Annotated
from operator import add


class IncidentWorkflowState(TypedDict):
    # --- Identity ---------------------------------------------------------
    incident_id: str
    raw_message: str
    source: str                         # e.g. "slack", "api", "pagerduty"
    slack_channel_id: Optional[str]
    slack_message_ts: Optional[str]

    # --- Classification results -------------------------------------------
    severity: Optional[str]             # P1 / P2 / P3
    confidence: Optional[float]         # 0.0 – 1.0
    title: Optional[str]
    summary: Optional[str]
    severity_reasoning: Optional[str]
    probable_domains: Optional[list[str]]
    impacted_systems: Optional[list[str]]

    # --- Responder resolution ---------------------------------------------
    responders: Optional[list[dict]]

    # --- Known-issue matching ---------------------------------------------
    known_issues: Optional[list[dict]]

    # --- Action planning --------------------------------------------------
    proposed_actions: Optional[list[dict]]

    # --- Approval gate ----------------------------------------------------
    approvals_required: Optional[bool]
    all_approved: Optional[bool]

    # --- Execution --------------------------------------------------------
    execution_results: Optional[list[dict]]

    # --- Tracking ---------------------------------------------------------
    audit_entries: Annotated[list[dict], add]   # append-only across nodes
    current_stage: str
    errors: Optional[list[str]]
