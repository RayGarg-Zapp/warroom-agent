"""
WarRoom Agent — LangGraph Workflow Definition

Builds and compiles the incident-response StateGraph.  The compiled graph
is exposed as the module-level singleton `incident_workflow` so that API
routes can simply ``from app.agents.workflow import incident_workflow``.

Flow:
  ingest_event
      |
  classify_incident
      |
  resolve_responders
      |
  lookup_known_issues
      |
  plan_actions
      |
  check_approval ──(wait)──> END  (paused — resumed via approval API)
      |
   (execute)
      |
  execute_actions
      |
  finalize_incident
      |
     END
"""

from langgraph.graph import StateGraph, END

from app.agents.state import IncidentWorkflowState
from app.agents.nodes import (
    ingest_event,
    classify_incident,
    resolve_responders,
    lookup_known_issues,
    plan_actions,
    check_approval,
    execute_actions,
    finalize_incident,
)


def build_incident_workflow() -> "CompiledStateGraph":  # noqa: F821
    """Build and compile the incident response workflow graph."""
    workflow = StateGraph(IncidentWorkflowState)

    # -- Nodes -------------------------------------------------------------
    workflow.add_node("ingest_event", ingest_event)
    workflow.add_node("classify_incident", classify_incident)
    workflow.add_node("resolve_responders", resolve_responders)
    workflow.add_node("lookup_known_issues", lookup_known_issues)
    workflow.add_node("plan_actions", plan_actions)
    workflow.add_node("execute_actions", execute_actions)
    workflow.add_node("finalize_incident", finalize_incident)

    # -- Edges (linear flow with one conditional branch) -------------------
    workflow.set_entry_point("ingest_event")
    workflow.add_edge("ingest_event", "classify_incident")
    workflow.add_edge("classify_incident", "resolve_responders")
    workflow.add_edge("resolve_responders", "lookup_known_issues")
    workflow.add_edge("lookup_known_issues", "plan_actions")

    # Conditional: high/critical-risk actions pause for human approval
    workflow.add_conditional_edges(
        "plan_actions",
        check_approval,
        {
            "wait": END,        # graph stops — approval arrives via REST API
            "execute": "execute_actions",
        },
    )

    workflow.add_edge("execute_actions", "finalize_incident")
    workflow.add_edge("finalize_incident", END)

    return workflow.compile()


# Singleton compiled workflow — import this from API routes
incident_workflow = build_incident_workflow()
